package com.airport.ai.devicetype;

import java.util.List;

/**
 * 系统预置8类标准能力类型，不可新增或删除（对应5.2.4A业务规则2、8.4.2节）
 */
public final class CapabilityCatalog {

    public static final List<String> ALL_CODES = List.of(
            "CAP_INFO_DISPLAY", "CAP_BAGGAGE_MEASURE", "CAP_OVERSIZE_ALERT", "CAP_FLIGHT_UPDATE",
            "CAP_NAVIGATION", "CAP_ESCORT", "CAP_NOTIFICATION", "CAP_SIM_STATUS"
    );

    private CapabilityCatalog() {}
}
