import SwiftUI

struct ContentView: View {
    @StateObject private var state = BMSState()

    var body: some View {
        NavigationSplitView {
            List(selection: $selection) {
                Label("Dashboard", systemImage: "gauge.with.dots.needle.67percent")
                    .tag(SidebarItem.dashboard)
                Label("Cells", systemImage: "square.grid.3x3.fill")
                    .tag(SidebarItem.cells)
                Label("Sunny Island 6048", systemImage: "sun.max.fill")
                    .tag(SidebarItem.sunnyIsland)
                Label("Settings", systemImage: "gearshape")
                    .tag(SidebarItem.settings)
            }
            .listStyle(.sidebar)
            .navigationSplitViewColumnWidth(min: 180, ideal: 200)
        } detail: {
            Group {
                switch selection {
                case .dashboard:
                    DashboardView(state: state)
                case .cells:
                    CellsView(state: state)
                case .sunnyIsland:
                    SunnyIslandView()
                case .settings:
                    SettingsView(state: state)
                }
            }
            .frame(minWidth: 640, minHeight: 480)
        }
        .onAppear {
            if !state.isListening {
                state.startListening()
            }
        }
        .onDisappear {
            state.stopListening()
        }
    }

    @State private var selection: SidebarItem? = .dashboard
}

private enum SidebarItem: Hashable {
    case dashboard
    case cells
    case sunnyIsland
    case settings
}