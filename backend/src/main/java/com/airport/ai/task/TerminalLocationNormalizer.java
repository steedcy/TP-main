package com.airport.ai.task;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 候机楼设施点位归一化器：
 * 1. 将 45 条标准用例及自然语言中的各类设施名称映射为当前 2000x600 地图标准 poiCode；
 * 2. 将超出当前规定范围的具体编号（如 20号登机口、H16登机口、C21、5号门 等）自动折叠映射为规定范围内的同类设施（GATE_01~GATE_06 / ENTRANCE_01~ENTRANCE_03）。
 */
public final class TerminalLocationNormalizer {

    private static final int GATE_COUNT = 6;
    private static final int ENTRANCE_COUNT = 3;

    private static final Pattern GATE_NUMBER_CN = Pattern.compile("(?:[A-Za-z]-?)?(\\d{1,3})\\s*号?登机口");
    private static final Pattern GATE_PREFIX_CODE = Pattern.compile("(?:^|[^A-Z0-9])(?:GATE[_-]?|[A-HJ-Z])(\\d{1,3})(?:$|[^A-Z0-9])", Pattern.CASE_INSENSITIVE);
    private static final Pattern ENTRANCE_NUMBER_CN = Pattern.compile("(\\d{1,2})\\s*号门|(\\d{1,2})\\s*号出入口");
    private static final Pattern ENTRANCE_CODE = Pattern.compile("ENTRANCE[_-]?(\\d{1,2})", Pattern.CASE_INSENSITIVE);

    private static final Map<String, String> KEYWORD_ALIASES = new LinkedHashMap<>();
    static {
        // 旧版 F2 兼容
        KEYWORD_ALIASES.put("F2_SERVICE_POINT", "SERVICE_DESK");
        KEYWORD_ALIASES.put("F2_BAGGAGE_POINT", "OVERSIZE_CHECKIN");
        KEYWORD_ALIASES.put("F2_TEST_GATE", "GATE_04");

        // 超规行李处置（1.1 ~ 1.15）
        KEYWORD_ALIASES.put("宠物托运专用通道", "PET_CHANNEL");
        KEYWORD_ALIASES.put("乐器专用打包托运点", "OVERSIZE_PACKING");
        KEYWORD_ALIASES.put("婴儿车打包托运处", "OVERSIZE_PACKING");
        KEYWORD_ALIASES.put("分装打包区", "OVERSIZE_PACKING");
        KEYWORD_ALIASES.put("超规行李打包区", "OVERSIZE_PACKING");
        KEYWORD_ALIASES.put("超规行李打包处", "OVERSIZE_PACKING");
        KEYWORD_ALIASES.put("超规行李封装区", "OVERSIZE_PACKING");
        KEYWORD_ALIASES.put("电池拆装", "OVERSIZE_PACKING");
        KEYWORD_ALIASES.put("轮椅电池处理区", "OVERSIZE_PACKING");
        KEYWORD_ALIASES.put("超规行李处理区", "OVERSIZE_CHECKIN");
        KEYWORD_ALIASES.put("超规行李托运口", "OVERSIZE_CHECKIN");
        KEYWORD_ALIASES.put("超规行李托运处", "OVERSIZE_CHECKIN");
        KEYWORD_ALIASES.put("超规行李收费处", "OVERSIZE_CHECKIN");
        KEYWORD_ALIASES.put("二次托运评估窗口", "OVERSIZE_CHECKIN");
        KEYWORD_ALIASES.put("托运办理处", "OVERSIZE_CHECKIN");
        KEYWORD_ALIASES.put("轮椅托运处", "OVERSIZE_CHECKIN");
        KEYWORD_ALIASES.put("超规行李仓库", "OVERSIZE_STORAGE");
        KEYWORD_ALIASES.put("超规行李寄存区", "OVERSIZE_STORAGE");
        KEYWORD_ALIASES.put("超规行李寄存处", "OVERSIZE_STORAGE");
        KEYWORD_ALIASES.put("指定领取柜台", "OVERSIZE_STORAGE");
        KEYWORD_ALIASES.put("行李分拣区", "BAGGAGE_CLAIM_W");
        KEYWORD_ALIASES.put("行李转盘", "BAGGAGE_CLAIM_W");
        KEYWORD_ALIASES.put("超规行李装载口", "BAGGAGE_CLAIM_E");
        KEYWORD_ALIASES.put("国内航班超规行李装载区", "BAGGAGE_CLAIM_E");
        KEYWORD_ALIASES.put("中转行李拦截区", "TRANSFER_COUNTER");
        KEYWORD_ALIASES.put("值机主任柜台", "CHECKIN_EAST");
        KEYWORD_ALIASES.put("无障碍值机柜台", "CHECKIN_WEST");
        KEYWORD_ALIASES.put("团队值机区", "CHECKIN_WEST");
        KEYWORD_ALIASES.put("高尔夫团队值机区", "CHECKIN_WEST");
        KEYWORD_ALIASES.put("值机柜台", "CHECKIN_WEST");
        KEYWORD_ALIASES.put("值机区", "CHECKIN_WEST");

        // 特殊旅客服务（2.1 ~ 2.15）
        KEYWORD_ALIASES.put("特殊旅客服务台", "SPECIAL_SERVICE_DESK");
        KEYWORD_ALIASES.put("医疗室", "FAC_FIRSTAID");
        KEYWORD_ALIASES.put("急救中心", "FAC_FIRSTAID");
        KEYWORD_ALIASES.put("母婴室", "FAC_NURSERY_MW");
        KEYWORD_ALIASES.put("母婴候机室", "FAC_NURSERY_MW");
        KEYWORD_ALIASES.put("特殊餐食登记处", "MEAL_VOUCHER_POINT");
        KEYWORD_ALIASES.put("餐食发放点", "MEAL_VOUCHER_POINT");
        KEYWORD_ALIASES.put("餐食发放登记处", "MEAL_VOUCHER_POINT");
        KEYWORD_ALIASES.put("优先通道", "SECURITY_MAIN");
        KEYWORD_ALIASES.put("安检口", "SECURITY_MAIN");
        KEYWORD_ALIASES.put("安全检查", "SECURITY_MAIN");
        KEYWORD_ALIASES.put("问询台", "CHECKIN_EAST");
        KEYWORD_ALIASES.put("远机位摆渡车", "SHUTTLE_GATE");
        KEYWORD_ALIASES.put("无障碍摆渡点", "SHUTTLE_GATE");
        KEYWORD_ALIASES.put("远机位摆渡点", "SHUTTLE_GATE");
        KEYWORD_ALIASES.put("飞机舷梯口", "SHUTTLE_GATE");
        KEYWORD_ALIASES.put("酒店班车点", "ENTRANCE_03");
        KEYWORD_ALIASES.put("大巴", "ENTRANCE_03");
        KEYWORD_ALIASES.put("到达口", "ENTRANCE_01");
        KEYWORD_ALIASES.put("到达厅出口", "ENTRANCE_01");
        KEYWORD_ALIASES.put("到达大厅服务台", "CHECKIN_EAST");
        KEYWORD_ALIASES.put("候机楼B口", "ENTRANCE_02");
        KEYWORD_ALIASES.put("出发大厅服务台", "CHECKIN_EAST");
        KEYWORD_ALIASES.put("出发大厅交接点", "ENTRANCE_02");
        KEYWORD_ALIASES.put("家属交接点", "ENTRANCE_02");
        KEYWORD_ALIASES.put("出发大厅", "ENTRANCE_02");

        // 航班变更应对（3.1 ~ 3.15）
        KEYWORD_ALIASES.put("改签柜台", "REBOOK_COUNTER");
        KEYWORD_ALIASES.put("退票柜台", "REBOOK_COUNTER");
        KEYWORD_ALIASES.put("团队改签柜台", "REBOOK_COUNTER");
        KEYWORD_ALIASES.put("改签退票柜台", "REBOOK_COUNTER");
        KEYWORD_ALIASES.put("中转柜台", "TRANSFER_COUNTER");
        KEYWORD_ALIASES.put("中转区", "TRANSFER_COUNTER");
        KEYWORD_ALIASES.put("值班经理接待点", "DUTY_MANAGER_DESK");
        KEYWORD_ALIASES.put("国际候机区服务台", "DUTY_MANAGER_DESK");
        KEYWORD_ALIASES.put("候机广播室", "SERVICE_DESK");
        KEYWORD_ALIASES.put("信息发布台", "SERVICE_DESK");
        KEYWORD_ALIASES.put("运行信息中心", "SERVICE_DESK");
        KEYWORD_ALIASES.put("候机休息区", "FAC_LOUNGE_MW");
        KEYWORD_ALIASES.put("候机区", "FAC_LOUNGE_MW");
        KEYWORD_ALIASES.put("新登机口", "GATE_04");
        KEYWORD_ALIASES.put("原登机口", "GATE_03");
        KEYWORD_ALIASES.put("机舱门口", "GATE_04");
    }

    private TerminalLocationNormalizer() {}

    /**
     * 将输入文本归一化为标准 poiCode；无法识别时返回原去除空白后的字符串。
     */
    public static String normalize(String raw) {
        if (raw == null) return null;
        String text = raw.trim();
        if (text.isEmpty()) return text;

        // 1. 括号内已含标准编码时优先提取
        int open = text.indexOf('('), close = text.indexOf(')', open + 1);
        if (open < 0) { open = text.indexOf('（'); close = text.indexOf('）', open + 1); }
        if (open >= 0 && close > open + 1) {
            String inner = text.substring(open + 1, close).trim();
            String normInner = normalizeSingle(inner);
            if (!normInner.equals(inner) || normInner.matches("[A-Z0-9_]+")) {
                return normInner;
            }
        }

        // 若含箭头串联（如 "分装打包区→托运口"），取主目标或首段有效点位
        if (text.contains("→")) {
            String[] parts = text.split("→");
            String last = normalizeSingle(parts[parts.length - 1]);
            if (last.matches("[A-Z0-9_]+")) return last;
        }
        return normalizeSingle(text);
    }

    private static String normalizeSingle(String text) {
        String trimmed = text.trim();
        String upper = trimmed.toUpperCase();

        // 2. 登机口号提取与范围折叠（超出 1~6 自动折叠到 GATE_01 ~ GATE_06）
        Matcher mGateCn = GATE_NUMBER_CN.matcher(trimmed);
        if (mGateCn.find()) {
            int n = Integer.parseInt(mGateCn.group(1));
            return formatGate(n);
        }
        Matcher mGateCode = GATE_PREFIX_CODE.matcher(upper);
        if (mGateCode.find() && !upper.startsWith("ENTRANCE")) {
            int n = Integer.parseInt(mGateCode.group(1));
            return formatGate(n);
        }

        // 3. 出入口号提取与范围折叠（超出 1~3 自动折叠到 ENTRANCE_01 ~ ENTRANCE_03）
        Matcher mEntCn = ENTRANCE_NUMBER_CN.matcher(trimmed);
        if (mEntCn.find()) {
            String g = mEntCn.group(1) != null ? mEntCn.group(1) : mEntCn.group(2);
            return formatEntrance(Integer.parseInt(g));
        }
        Matcher mEntCode = ENTRANCE_CODE.matcher(upper);
        if (mEntCode.find()) {
            return formatEntrance(Integer.parseInt(mEntCode.group(1)));
        }

        // 4. 精确与关键词别名匹配
        for (Map.Entry<String, String> entry : KEYWORD_ALIASES.entrySet()) {
            if (upper.equals(entry.getKey().toUpperCase()) || trimmed.contains(entry.getKey())) {
                return entry.getValue();
            }
        }
        return trimmed;
    }

    private static String formatGate(int num) {
        int clamped = ((Math.max(1, num) - 1) % GATE_COUNT) + 1;
        return String.format("GATE_%02d", clamped);
    }

    private static String formatEntrance(int num) {
        int clamped = ((Math.max(1, num) - 1) % ENTRANCE_COUNT) + 1;
        return String.format("ENTRANCE_%02d", clamped);
    }
}
