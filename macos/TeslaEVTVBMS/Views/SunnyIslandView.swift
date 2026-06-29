import SwiftUI

struct SunnyIslandView: View {
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                Text("Sunny Island 6048-US Setup")
                    .font(.title2.bold())

                Text("Connect your EVTV BMS to the SMA Sunny Island 6048-US over CAN at 500 kbps.")
                    .foregroundStyle(.secondary)

                SetupSection(title: "1. CAN Wiring", icon: "cable.connector") {
                    SetupStep("Move the termination plug from ComSync Out → ComSync In on the inverter.")
                    SetupStep("Run a CAT5 cable from EVTV Due CAN (3.5mm jack) to ComSync In.")
                    PinoutTable()
                    SetupStep("Enable termination on EVTV: TERMEN=1 via USB serial.")
                }

                SetupSection(title: "2. EVTV Due Settings", icon: "terminal") {
                    CodeBlock(text: """
                    CANSPEED=500000
                    TERMEN=1
                    MAXAH=<pack Ah × 10>
                    CURRAH=<current Ah × 10>
                    """)
                }

                SetupSection(title: "3. Sunny Island QCG", icon: "gearshape.2") {
                    SetupStep("Firmware 7.3 or newer required.")
                    SetupStep("DC breaker ON → hold ENTER at \"To init system\" until 3 beeps.")
                    SetupStep("Battery type: LiIon_Ext-BMS")
                    SetupStep("Nominal capacity: your pack Ah (e.g. 150 Ah for 2 modules).")
                }

                SetupSection(title: "4. Verify", icon: "checkmark.circle") {
                    SetupStep("SOC should update on the Sunny Island display.")
                    SetupStep("Freq Shift and TCCH Amps appear on the Dashboard when SMA integration is active.")
                    SetupStep("F952 fault = CAN timeout — check wiring, baud rate, and termination.")
                }

                WarningBanner(
                    text: "The 6048-US requires closed-loop BMS communication. Open-loop voltage-only mode is not supported for lithium batteries."
                )
            }
            .padding(24)
        }
    }
}

struct SetupSection<Content: View>: View {
    let title: String
    let icon: String
    @ViewBuilder let content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Label(title, systemImage: icon)
                .font(.headline)
            content
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.background, in: RoundedRectangle(cornerRadius: 12))
    }
}

struct SetupStep: View {
    let text: String
    init(_ text: String) { self.text = text }

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            Image(systemName: "circle.fill")
                .font(.system(size: 6))
                .padding(.top, 6)
                .foregroundStyle(.secondary)
            Text(text)
                .font(.subheadline)
        }
    }
}

struct PinoutTable: View {
    var body: some View {
        VStack(spacing: 0) {
            PinRow(pin: "2", signal: "CAN_GND")
            Divider()
            PinRow(pin: "4", signal: "CAN_H")
            Divider()
            PinRow(pin: "5", signal: "CAN_L")
        }
        .background(Color.secondary.opacity(0.08), in: RoundedRectangle(cornerRadius: 8))
        .padding(.vertical, 4)
    }
}

struct PinRow: View {
    let pin: String
    let signal: String

    var body: some View {
        HStack {
            Text("Pin \(pin)")
                .font(.caption.weight(.semibold))
                .frame(width: 50, alignment: .leading)
            Text(signal)
                .font(.caption.monospaced())
            Spacer()
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
    }
}

struct CodeBlock: View {
    let text: String

    var body: some View {
        Text(text)
            .font(.system(.caption, design: .monospaced))
            .padding(12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color.black.opacity(0.06), in: RoundedRectangle(cornerRadius: 8))
    }
}

struct WarningBanner: View {
    let text: String

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: "exclamationmark.triangle.fill")
                .foregroundStyle(.orange)
            Text(text)
                .font(.subheadline)
        }
        .padding(14)
        .background(.orange.opacity(0.12), in: RoundedRectangle(cornerRadius: 10))
    }
}