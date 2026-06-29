import SwiftUI

struct CellsView: View {
    @ObservedObject var state: BMSState

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Cell Voltages")
                    .font(.title2.bold())

                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                    CellMetric(title: "Lowest Cell", value: state.values["lowest_cell"], tint: .orange)
                    CellMetric(title: "Average Cell", value: state.values["average_cell"], tint: .blue)
                    CellMetric(title: "Highest Cell", value: state.values["highest_cell"], tint: .green)
                }

                HStack(spacing: 12) {
                    CellMetric(title: "Cell Spread", value: state.cellDifference, tint: .red)
                    CellMetric(title: "Active Cells", value: state.values["active_cells"], tint: .purple, format: "%.0f")
                    CellMetric(title: "Max Cells", value: state.values["max_cells"], tint: .gray, format: "%.0f")
                }

                if let low = state.values["lowest_cell"],
                   let high = state.values["highest_cell"],
                   high > low {
                    CellBalanceBar(low: low, high: high, avg: state.values["average_cell"] ?? (low + high) / 2)
                }
            }
            .padding(24)
        }
    }
}

struct CellMetric: View {
    let title: String
    let value: Double?
    let tint: Color
    var format: String = "%.3f V"

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title)
                .font(.caption.weight(.semibold))
                .foregroundStyle(tint)
            Text(value.map { String(format: format, $0) } ?? "—")
                .font(.title3.weight(.semibold))
                .monospacedDigit()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(16)
        .background(.background, in: RoundedRectangle(cornerRadius: 12))
    }
}

struct CellBalanceBar: View {
    let low: Double
    let high: Double
    let avg: Double

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Cell Balance")
                .font(.headline)
            GeometryReader { geo in
                let range = max(high - low, 0.001)
                let avgPos = (avg - low) / range

                ZStack(alignment: .leading) {
                    Capsule().fill(Color.secondary.opacity(0.15))
                    Capsule()
                        .fill(LinearGradient(colors: [.orange, .green], startPoint: .leading, endPoint: .trailing))
                        .frame(width: geo.size.width * 0.9)
                    Circle()
                        .fill(.white)
                        .frame(width: 10, height: 10)
                        .shadow(radius: 2)
                        .offset(x: geo.size.width * avgPos - 5)
                }
            }
            .frame(height: 16)
            HStack {
                Text(String(format: "%.3f V", low))
                Spacer()
                Text(String(format: "%.3f V", high))
            }
            .font(.caption)
            .foregroundStyle(.secondary)
        }
        .padding(16)
        .background(.background, in: RoundedRectangle(cornerRadius: 12))
    }
}