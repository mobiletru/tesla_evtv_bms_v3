import Foundation

enum CANParser {
    private static let recognizedIDs: Set<UInt32> = [0x150, 0x151, 0x650, 0x651, 0x683]

    static func parse(payload: Data, port: Int) -> [String: Double]? {
        guard payload.count >= 12 else { return nil }

        let canID = UInt32(payload[8])
            | (UInt32(payload[9]) << 8)
            | (UInt32(payload[10]) << 16)
            | (UInt32(payload[11]) << 24)

        guard recognizedIDs.contains(canID) else { return nil }

        var result: [String: Double] = [:]

        switch canID {
        case 0x650:
            result["state_of_charge"] = Double(payload[0]) / 2.0

        case 0x651:
            result["lowest_cell"] = u16(payload[0], payload[1]) / 1000.0
            result["highest_cell"] = u16(payload[2], payload[3]) / 1000.0
            result["average_cell"] = u16(payload[4], payload[5]) / 1000.0
            result["max_cells"] = Double(payload[6])
            result["active_cells"] = Double(payload[7])

        case 0x151:
            let current = Double(s32(payload[0..<4])) / 100.0
            let power = Double(s32(payload[4..<8])) / 100.0
            let volts = current != 0 ? power / current : 0
            result["current"] = (current * 100).rounded() / 100
            result["power"] = power.rounded()
            result["volts"] = (volts * 10).rounded() / 10

        case 0x683:
            result["freq_shift_volts"] = u16(payload[2], payload[3]) / 100.0
            result["tcch_amps"] = u16(payload[4], payload[5]) / 10.0

        case 0x150:
            let current = s16(payload[0], payload[1]) * -1.0
            let volts = u16(payload[2], payload[3]) / 10.0
            let power = (volts * current).rounded()
            result["current"] = (current * 100).rounded() / 100
            result["power"] = power
            result["volts"] = (volts * 10).rounded() / 10
            result["max_temp"] = cToF(Double(payload[6]))
            result["min_temp"] = cToF(Double(payload[7]))

        default:
            return nil
        }

        _ = port
        return result
    }

    private static func u16(_ b0: UInt8, _ b1: UInt8) -> Double {
        Double(b0) + Double(b1) << 8
    }

    private static func s16(_ b0: UInt8, _ b1: UInt8) -> Double {
        Double(Int16(bitPattern: UInt16(b0) | (UInt16(b1) << 8)))
    }

    private static func s32(_ bytes: Data.SubSequence) -> Int32 {
        var value: Int32 = 0
        for (index, byte) in bytes.enumerated() {
            value |= Int32(byte) << (index * 8)
        }
        return value
    }

    private static func cToF(_ celsius: Double) -> Double {
        ((celsius * 9.0 / 5.0 + 32.0) * 10).rounded() / 10
    }
}