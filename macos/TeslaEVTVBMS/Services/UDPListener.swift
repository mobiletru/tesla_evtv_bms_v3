import Foundation
import Darwin

final class UDPListener {
    private var socketFD: Int32 = -1
    private var readSource: DispatchSourceRead?
    private let queue = DispatchQueue(label: "com.evtv.bms.udp", qos: .userInitiated)
    private let onPacket: @Sendable ([String: Double]) -> Void

    init(onPacket: @escaping @Sendable ([String: Double]) -> Void) {
        self.onPacket = onPacket
    }

    func start(port: UInt16) {
        stop()

        socketFD = Darwin.socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)
        guard socketFD >= 0 else { return }

        var reuse: Int32 = 1
        setsockopt(socketFD, SOL_SOCKET, SO_REUSEADDR, &reuse, socklen_t(MemoryLayout<Int32>.size))

        var addr = sockaddr_in()
        addr.sin_len = UInt8(MemoryLayout<sockaddr_in>.size)
        addr.sin_family = sa_family_t(AF_INET)
        addr.sin_port = port.bigEndian
        addr.sin_addr.s_addr = INADDR_ANY.bigEndian

        let bindResult = withUnsafePointer(to: &addr) {
            $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                Darwin.bind(socketFD, $0, socklen_t(MemoryLayout<sockaddr_in>.size))
            }
        }
        guard bindResult == 0 else {
            stop()
            return
        }

        let source = DispatchSource.makeReadSource(fileDescriptor: socketFD, queue: queue)
        source.setEventHandler { [weak self] in
            self?.readPacket()
        }
        source.setCancelHandler { [weak self] in
            guard let self, self.socketFD >= 0 else { return }
            Darwin.close(self.socketFD)
            self.socketFD = -1
        }
        source.resume()
        readSource = source
    }

    func stop() {
        readSource?.cancel()
        readSource = nil
        if socketFD >= 0 {
            Darwin.close(socketFD)
            socketFD = -1
        }
    }

    private func readPacket() {
        var buffer = [UInt8](repeating: 0, count: 1024)
        let received = buffer.withUnsafeMutableBytes { ptr -> Int in
            guard let base = ptr.baseAddress else { return 0 }
            return Darwin.recv(socketFD, base, 1024, 0)
        }
        guard received > 0 else { return }

        let data = Data(buffer.prefix(received))
        guard let parsed = CANParser.parse(payload: data, port: 0) else { return }
        onPacket(parsed)
    }
}