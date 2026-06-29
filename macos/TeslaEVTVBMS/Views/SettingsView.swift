import SwiftUI

struct SettingsView: View {
    @ObservedObject var state: BMSState

    var body: some View {
        Form {
            Section("Pack") {
                TextField("Pack Name", text: $state.packName)
                Stepper(value: $state.packSizeKWh, in: 1...500, step: 1) {
                    HStack {
                        Text("Pack Size")
                        Spacer()
                        Text("\(Int(state.packSizeKWh)) kWh")
                            .foregroundStyle(.secondary)
                    }
                }
            }

            Section("UDP Listener") {
                Stepper(value: $state.udpPort, in: 1024...65535) {
                    HStack {
                        Text("Port")
                        Spacer()
                        Text("\(state.udpPort)")
                            .foregroundStyle(.secondary)
                            .monospacedDigit()
                    }
                }

                HStack {
                    Text("Status")
                    Spacer()
                    Text(state.isListening ? "Listening" : "Stopped")
                        .foregroundStyle(state.isListening ? .green : .secondary)
                }

                Button(state.isListening ? "Stop Listener" : "Start Listener") {
                    if state.isListening {
                        state.stopListening()
                    } else {
                        state.startListening()
                    }
                }

                Button("Apply Port & Restart") {
                    state.restartListening()
                }
                .disabled(!state.isListening)
            }

            Section("About") {
                LabeledContent("Version", value: "1.0.0")
                LabeledContent("Protocol", value: "EVTV BMS UDP/CAN")
                LabeledContent("Default Port", value: "6850")
            }
        }
        .formStyle(.grouped)
        .padding()
    }
}