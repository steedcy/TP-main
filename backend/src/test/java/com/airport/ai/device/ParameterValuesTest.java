package com.airport.ai.device;
import org.junit.jupiter.api.Test;
import java.util.Map;
import static org.junit.jupiter.api.Assertions.*;
class ParameterValuesTest {
    private static final String SCHEMA="[{\"name\":\"duration\",\"type\":\"Integer\",\"required\":true,\"defaultValue\":\"60\",\"range\":\"10~600\"}]";
    @Test void appliesTypedDefaults() { assertEquals(Map.of("duration",60),ParameterValues.materialize(SCHEMA,Map.of())); }
    @Test void rejectsUnknownFractionAndOutOfRange() {
        assertThrows(IllegalArgumentException.class,()->ParameterValues.materialize(SCHEMA,Map.of("checkContent",true)));
        assertThrows(IllegalArgumentException.class,()->ParameterValues.materialize(SCHEMA,Map.of("duration",10.5)));
        assertThrows(IllegalArgumentException.class,()->ParameterValues.materialize(SCHEMA,Map.of("duration",601)));
    }
}
