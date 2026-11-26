package com.airport.ai.simulator;

import org.springframework.stereotype.Component;

import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;

@Component
public class MobileRobotDriver implements CapabilityDriver {
    @org.springframework.beans.factory.annotation.Autowired
    private SimulatorProperties properties = new SimulatorProperties();
    @Override public String deviceType() { return "MOBILE_ROBOT"; }
    @Override public Set<String> capabilities() { return Set.of("CAP_NAVIGATION", "CAP_ESCORT", "CAP_NOTIFICATION", "CAP_INFO_DISPLAY"); }

    @Override
    public Map<String, Object> execute(String capabilityType, Map<String, Object> input) {
        return switch (capabilityType) {
            case "CAP_NAVIGATION" -> navigation(input);
            case "CAP_ESCORT" -> escort(input);
            case "CAP_NOTIFICATION" -> notification(input);
            case "CAP_INFO_DISPLAY" -> display(input);
            default -> throw new IllegalArgumentException("移动服务机器人不支持能力 " + capabilityType);
        };
    }

    @Override
    public List<SimulatorProtocol.Location> routeLocations(String capabilityType, Map<String, Object> input,
                                                           SimulatorProtocol.Location current, Map<String, Object> output) {
        if (!Set.of("CAP_NAVIGATION", "CAP_ESCORT").contains(capabilityType)) return List.of();
        String target = required(input, "targetLocation").trim();
        var point = resolveTargetPoint(target);
        if (point == null || point.size() != 2) throw new IllegalArgumentException("目标位置未标定: " + target);
        double targetX = point.get(0), targetY = point.get(1);
        if (targetX < 0 || targetX > 2000 || targetY < 0 || targetY > 6895) {
            throw new IllegalArgumentException("目标坐标超出候机楼底图范围");
        }
        double startX = current.x().doubleValue();
        double startY = current.y().doubleValue();
        boolean trackIsolationZone = "隔离区内".equals(current.zone()) || "隔离区外".equals(current.zone());

        // 2000x600 室内地图：跨越隔离区边界（y=235..341）时，绕行中央安全检查通道（x=1038），避开两侧不可通行商铺区
        List<double[]> anchors = new ArrayList<>();
        anchors.add(new double[]{startX, startY});
        if (startY <= 600 && targetY <= 600 && ((startY > 235 && targetY <= 235) || (startY <= 235 && targetY > 235))) {
            if (startY > 235) {
                anchors.add(new double[]{startX, 425.0});
                anchors.add(new double[]{1038.0, 425.0});
                anchors.add(new double[]{1038.0, 286.0});
                anchors.add(new double[]{1038.0, 115.0});
                anchors.add(new double[]{targetX, 115.0});
            } else {
                anchors.add(new double[]{startX, 115.0});
                anchors.add(new double[]{1038.0, 115.0});
                anchors.add(new double[]{1038.0, 286.0});
                anchors.add(new double[]{1038.0, 425.0});
                anchors.add(new double[]{targetX, 425.0});
            }
        }
        anchors.add(new double[]{targetX, targetY});

        List<double[]> densePoints = densifyPolyline(anchors, 24);
        List<SimulatorProtocol.Location> path = new ArrayList<>(densePoints.size());
        for (double[] wp : densePoints) {
            String z = trackIsolationZone ? (wp[1] < 235.0 ? "隔离区内" : "隔离区外") : current.zone();
            path.add(new SimulatorProtocol.Location(
                    java.math.BigDecimal.valueOf(Math.round(wp[0] * 100.0) / 100.0),
                    java.math.BigDecimal.valueOf(Math.round(wp[1] * 100.0) / 100.0),
                    z));
        }
        return path;
    }

    private static List<double[]> densifyPolyline(List<double[]> anchors, int steps) {
        List<double[]> out = new ArrayList<>();
        if (anchors.size() < 2) return out;
        double[] segLen = new double[anchors.size() - 1];
        double total = 0;
        for (int i = 0; i < segLen.length; i++) {
            segLen[i] = Math.hypot(anchors.get(i + 1)[0] - anchors.get(i)[0], anchors.get(i + 1)[1] - anchors.get(i)[1]);
            total += segLen[i];
        }
        if (total < 1e-6) {
            for (int i = 0; i < steps; i++) out.add(anchors.get(anchors.size() - 1));
            return out;
        }
        for (int s = 1; s <= steps; s++) {
            double targetDist = total * s / steps;
            double acc = 0;
            for (int i = 0; i < segLen.length; i++) {
                double nextAcc = acc + segLen[i];
                if (targetDist <= nextAcc + 1e-6 || i == segLen.length - 1) {
                    double ratio = segLen[i] <= 1e-6 ? 1.0 : Math.min(1.0, Math.max(0.0, (targetDist - acc) / segLen[i]));
                    double x = anchors.get(i)[0] + (anchors.get(i + 1)[0] - anchors.get(i)[0]) * ratio;
                    double y = anchors.get(i)[1] + (anchors.get(i + 1)[1] - anchors.get(i)[1]) * ratio;
                    out.add(new double[]{x, y});
                    break;
                }
                acc = nextAcc;
            }
        }
        return out;
    }

    private List<Double> resolveTargetPoint(String target) {
        var direct = properties.getLandmarks().get(target);
        if (direct != null && direct.size() == 2) return direct;
        // 支持形如 "4号登机口(GATE_04)" 提取括号内的标准点位编码
        int open = target.indexOf('('), close = target.indexOf(')', open + 1);
        if (open < 0) { open = target.indexOf('（'); close = target.indexOf('）', open + 1); }
        if (open >= 0 && close > open + 1) {
            String inner = target.substring(open + 1, close).trim();
            var byCode = properties.getLandmarks().get(inner);
            if (byCode != null && byCode.size() == 2) return byCode;
        }
        // 自动折叠超出当前规定范围的登机口/出入口编号（如 20号登机口 / H16 / 5号门）
        var gateM = java.util.regex.Pattern.compile("(?:[A-Za-z]-?)?(\\d{1,3})\\s*号?登机口|^GATE[_-]?(\\d{1,3})$|^[A-HJ-Z](\\d{1,3})$", java.util.regex.Pattern.CASE_INSENSITIVE).matcher(target);
        if (gateM.find()) {
            String g = gateM.group(1) != null ? gateM.group(1) : (gateM.group(2) != null ? gateM.group(2) : gateM.group(3));
            int num = ((Math.max(1, Integer.parseInt(g)) - 1) % 6) + 1;
            var byGate = properties.getLandmarks().get(String.format("GATE_%02d", num));
            if (byGate != null && byGate.size() == 2) return byGate;
        }
        var entM = java.util.regex.Pattern.compile("(\\d{1,2})\\s*号门|(\\d{1,2})\\s*号出入口|^ENTRANCE[_-]?(\\d{1,2})$", java.util.regex.Pattern.CASE_INSENSITIVE).matcher(target);
        if (entM.find()) {
            String g = entM.group(1) != null ? entM.group(1) : (entM.group(2) != null ? entM.group(2) : entM.group(3));
            int num = ((Math.max(1, Integer.parseInt(g)) - 1) % 3) + 1;
            var byEnt = properties.getLandmarks().get(String.format("ENTRANCE_%02d", num));
            if (byEnt != null && byEnt.size() == 2) return byEnt;
        }
        return null;
    }

    private Map<String, Object> navigation(Map<String, Object> input) {
        String target = required(input, "targetLocation");
        String preference = String.valueOf(input.getOrDefault("routePreference", "SHORTEST"));
        if (!Set.of("SHORTEST", "BARRIER_FREE").contains(preference)) throw new IllegalArgumentException("routePreference取值非法");
        int seed = target.hashCode() & 0x7fffffff;
        return Map.of("routeGenerated", true, "estimatedDistance", 25.0 + seed % 476,
                "estimatedDuration", 30 + seed % 571, "waypointCount", 2 + seed % 12);
    }

    private Map<String, Object> escort(Map<String, Object> input) {
        required(input, "targetLocation");
        String mode = required(input, "escortMode");
        if (!Set.of("LEAD", "FOLLOW").contains(mode)) throw new IllegalArgumentException("escortMode必须为LEAD/FOLLOW");
        int duration = range(input, "maxDuration", 60, 1800);
        return Map.of("arrivalStatus", "ARRIVED", "actualDistance", 85.2, "actualDuration", Math.min(420, duration));
    }

    private Map<String, Object> notification(Map<String, Object> input) {
        String type = required(input, "notificationType");
        if (!Set.of("VOICE", "TEXT", "BOTH").contains(type)) throw new IllegalArgumentException("notificationType取值非法");
        required(input, "notificationContent");
        int repeats = range(input, "repeatCount", 1, 5);
        return Map.of("notificationStatus", "SUCCESS", "actualRepeatCount", repeats);
    }

    private Map<String, Object> display(Map<String, Object> input) {
        String type = required(input, "contentType");
        if (!Set.of("TEXT", "IMAGE", "VIDEO", "HTML").contains(type)) throw new IllegalArgumentException("contentType取值非法");
        required(input, "contentData");
        int duration = range(input, "displayDuration", 5, 300);
        return Map.of("displayStatus", "SUCCESS", "actualDuration", duration, "errorMessage", "");
    }

    private String required(Map<String, Object> input, String field) {
        Object value = input.get(field);
        if (value == null || value.toString().isBlank()) throw new IllegalArgumentException(field + "不能为空");
        return value.toString();
    }
    private int range(Map<String, Object> input, String field, int min, int max) {
        Object value = input.get(field);
        if (!(value instanceof Number n) || n.doubleValue() != n.intValue() || n.intValue() < min || n.intValue() > max)
            throw new IllegalArgumentException(field + "范围必须为" + min + "~" + max);
        return n.intValue();
    }
}
