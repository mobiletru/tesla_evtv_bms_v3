import Foundation
import SwiftUI

enum BatteryStatus: String {
    case charging = "Charging"
    case discharging = "Discharging"
    case idle = "Idle"
    case unknown = "Unknown"
}

@MainActor
final class BMSState: ObservableObject {
    @AppStorage("packName") var packName = "Tesla Pack"
    @AppStorage("udpPort") var udpPort = 6850
    @AppStorage("packSizeKWh") var packSizeKWh = 75.0

    @Published var isListening = false
    @Published var lastUpdate: Date?
    @Published var values: [String: Double] = [:]

    @Published var chargeEnergyKWh = 0.0
    @Published var dischargeEnergyKWh = 0.0

    private var listener: UDPListener?
    private var energyLastUpdate = Date()

    var stateOfCharge: Double? { values["state_of_charge"] }
    var volts: Double? { values["volts"] }
    var current: Double? { values["current"] }
    var power: Double? { values["power"] }

    var batteryStatus: BatteryStatus {
        guard let current else { return .unknown }
        if current > 1 { return .charging }
        if current < -1 { return .discharging }
        return .idle
    }

    var availableEnergyKWh: Double? {
        guard let soc = stateOfCharge else { return nil }
        return (packSizeKWh * soc / 100.0 * 100).rounded() / 100
    }

    var cellDifference: Double? {
        guard let low = values["lowest_cell"], let high = values["highest_cell"] else { return nil }
        return ((high - low) * 10000).rounded() / 10000
    }

    var chargePower: Double {
        guard let power, power > 0 else { return 0 }
        return power
    }

    var dischargePower: Double {
        guard let power, power < 0 else { return 0 }
        return abs(power)
    }

    var summary: String {
        switch batteryStatus {
        case .discharging:
            if let energy = availableEnergyKWh, let power, abs(power) > 0 {
                let hours = energy / (abs(power) / 1000.0)
                return formatHours(hours, suffix: "to Empty")
            }
            return "Discharging"
        case .charging:
            if let energy = availableEnergyKWh, let power, abs(power) > 0 {
                let hours = (packSizeKWh - energy) / (abs(power) / 1000.0)
                return formatHours(hours, suffix: "to Full")
            }
            return "Charging"
        case .idle:
            return "Idle"
        case .unknown:
            return "Waiting for data…"
        }
    }

    func startListening() {
        listener = UDPListener { [weak self] parsed in
            Task { @MainActor in
                self?.merge(parsed)
            }
        }
        listener?.start(port: UInt16(udpPort))
        isListening = true
        energyLastUpdate = Date()
    }

    func stopListening() {
        listener?.stop()
        listener = nil
        isListening = false
    }

    func restartListening() {
        stopListening()
        startListening()
    }

    func resetEnergy() {
        chargeEnergyKWh = 0
        dischargeEnergyKWh = 0
        energyLastUpdate = Date()
    }

    private func merge(_ parsed: [String: Double]) {
        values.merge(parsed) { _, new in new }
        lastUpdate = Date()

        let updatesPower = parsed.keys.contains("power") || parsed.keys.contains("current")
        if updatesPower, let power {
            let now = Date()
            let delta = now.timeIntervalSince(energyLastUpdate)
            energyLastUpdate = now

            if power < 0 {
                dischargeEnergyKWh += (abs(power) * delta / 3600.0) / 1000.0
            } else if power > 0 {
                chargeEnergyKWh += (power * delta / 3600.0) / 1000.0
            }

            values["charge_energy"] = (chargeEnergyKWh * 1000).rounded() / 1000
            values["discharge_energy"] = (dischargeEnergyKWh * 1000).rounded() / 1000
            values["charge"] = chargePower
            values["discharge"] = dischargePower
        }

        if let soc = stateOfCharge {
            values["available_energy"] = availableEnergyKWh ?? 0
            _ = soc
        }

        if let diff = cellDifference {
            values["cell_difference"] = diff
        }

        values["battery_status"] = statusCode(for: batteryStatus)
    }

    private func statusCode(for status: BatteryStatus) -> Double {
        switch status {
        case .charging: return 1
        case .discharging: return 2
        case .idle: return 0
        case .unknown: return -1
        }
    }

    private func formatHours(_ hours: Double, suffix: String) -> String {
        if hours <= 0 { return "Idle" }
        let formatted = hours < 10 ? String(format: "%.1f", hours) : String(Int(hours.rounded()))
        return "\(formatted) hrs \(suffix)"
    }
}