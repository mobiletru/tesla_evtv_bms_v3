import SwiftUI

struct DashboardView: View {
    @ObservedObject var state: BMSState

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                header
                socCard
                powerGrid
                energyRow
                inverterRow
                statusFooter
            }
            .padding(24)
        }
        .background(Color(nsColor: .windowBackgroundColor))
    }

    private var header: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text(state.packName)
                    .font(.title.bold())
                Text(state.isListening ? "Listening on UDP port \(state.udpPort)" : "Not listening")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            ConnectionBadge(isListening: state.isListening, lastUpdate: state.lastUpdate)
        }
    }

    private var socCard: some View {
        HStack(spacing: 24) {
            ZStack {
                Circle()
                    .stroke(Color.secondary.opacity(0.2), lineWidth: 12)
                Circle()
                    .trim(from: 0, to: CGFloat((state.stateOfCharge ?? 0) / 100.0))
                    .stroke(socColor, style: StrokeStyle(lineWidth: 12, lineCap: .round))
                    .rotationEffect(.degrees(-90))
                    .animation(.easeInOut(duration: 0.4), value: state.stateOfCharge)
                VStack(spacing: 2) {
                    Text(format(state.stateOfCharge, suffix: "%"))
                        .font(.system(size: 36, weight: .bold, design: .rounded))
                    Text("SOC")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .frame(width: 140, height: 140)

            VStack(alignment: .leading, spacing: 12) {
                Text(state.summary)
                    .font(.title2.weight(.semibold))
                Label(state.batteryStatus.rawValue, systemImage: statusIcon)
                    .font(.headline)
                    .foregroundStyle(statusColor)
                if let available = state.availableEnergyKWh {
                    Text("\(String(format: "%.1f", available)) / \(String(format: "%.0f", state.packSizeKWh)) kWh available")
                        .foregroundStyle(.secondary)
                }
            }
            Spacer()
        }
        .padding(20)
        .background(.background, in: RoundedRectangle(cornerRadius: 16))
    }

    private var powerGrid: some View {
        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible()), GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
            MetricTile(title: "Voltage", value: format(state.volts, suffix: " V"), icon: "bolt.car.fill", tint: .blue)
            MetricTile(title: "Current", value: format(state.current, suffix: " A"), icon: "arrow.left.arrow.right", tint: .orange)
            MetricTile(title: "Power", value: format(state.power, suffix: " W"), icon: "bolt.fill", tint: .yellow)
            MetricTile(title: "Pack Temp", value: tempRange, icon: "thermometer.medium", tint: .red)
        }
    }

    private var energyRow: some View {
        HStack(spacing: 12) {
            MetricTile(title: "Charge Energy", value: format(state.values["charge_energy"], suffix: " kWh"), icon: "arrow.down.circle.fill", tint: .green)
            MetricTile(title: "Discharge Energy", value: format(state.values["discharge_energy"], suffix: " kWh"), icon: "arrow.up.circle.fill", tint: .purple)
        }
    }

    private var inverterRow: some View {
        HStack(spacing: 12) {
            MetricTile(title: "Freq Shift", value: format(state.values["freq_shift_volts"], suffix: " V"), icon: "waveform.path", tint: .cyan)
            MetricTile(title: "TCCH Amps", value: format(state.values["tcch_amps"], suffix: " A"), icon: "cable.connector", tint: .indigo)
        }
    }

    private var statusFooter: some View {
        HStack {
            if let last = state.lastUpdate {
                Text("Last update: \(last.formatted(date: .omitted, time: .standard))")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Button("Reset Energy Counters") {
                state.resetEnergy()
            }
            .buttonStyle(.bordered)
        }
    }

    private var socColor: Color {
        guard let soc = state.stateOfCharge else { return .gray }
        if soc > 50 { return .green }
        if soc > 20 { return .orange }
        return .red
    }

    private var statusIcon: String {
        switch state.batteryStatus {
        case .charging: return "battery.100.bolt"
        case .discharging: return "battery.25"
        case .idle: return "battery.50"
        case .unknown: return "questionmark.circle"
        }
    }

    private var statusColor: Color {
        switch state.batteryStatus {
        case .charging: return .green
        case .discharging: return .orange
        case .idle: return .secondary
        case .unknown: return .gray
        }
    }

    private var tempRange: String {
        let minT = state.values["min_temp"]
        let maxT = state.values["max_temp"]
        if let minT, let maxT {
            return "\(Int(minT))–\(Int(maxT)) °F"
        }
        return "—"
    }

    private func format(_ value: Double?, suffix: String) -> String {
        guard let value else { return "—" }
        if suffix == "%" { return String(format: "%.0f%@", value, suffix) }
        if suffix == " W" || suffix == " A" { return String(format: "%.1f%@", value, suffix) }
        if suffix == " V" { return String(format: "%.1f%@", value, suffix) }
        if suffix == " kWh" { return String(format: "%.3f%@", value, suffix) }
        return String(format: "%.2f%@", value, suffix)
    }
}

struct MetricTile: View {
    let title: String
    let value: String
    let icon: String
    let tint: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label(title, systemImage: icon)
                .font(.caption.weight(.semibold))
                .foregroundStyle(tint)
            Text(value)
                .font(.title3.weight(.semibold))
                .monospacedDigit()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(16)
        .background(.background, in: RoundedRectangle(cornerRadius: 12))
    }
}

struct ConnectionBadge: View {
    let isListening: Bool
    let lastUpdate: Date?

    var body: some View {
        HStack(spacing: 6) {
            Circle()
                .fill(isActive ? .green : .orange)
                .frame(width: 8, height: 8)
            Text(isActive ? "Live" : isListening ? "Waiting" : "Stopped")
                .font(.caption.weight(.semibold))
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(.quaternary, in: Capsule())
    }

    private var isActive: Bool {
        guard let lastUpdate else { return false }
        return Date().timeIntervalSince(lastUpdate) < 5
    }
}