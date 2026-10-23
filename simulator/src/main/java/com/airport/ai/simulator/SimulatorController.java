package com.airport.ai.simulator;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.util.Map;

@RestController
@RequestMapping("/device-api/v1")
public class SimulatorController {
    private final SimulatorRuntime runtime;
    public SimulatorController(SimulatorRuntime runtime) { this.runtime = runtime; }

    @GetMapping("/health")
    public SimulatorProtocol.HealthResponse health(@RequestParam String nonce, HttpServletRequest request) {
        authenticate(request);
        return runtime.health(nonce);
    }

    @PostMapping("/agents/{agentCode}/binding")
    public Map<String, String> bind(@PathVariable String agentCode, @RequestBody SimulatorProtocol.BindingRequest binding,
                                    HttpServletRequest request) {
        authenticate(request);
        try { runtime.bind(agentCode, binding); }
        catch (IllegalArgumentException ex) { throw new ResponseStatusException(HttpStatus.BAD_REQUEST, ex.getMessage()); }
        return Map.of("status", "BOUND", "agentCode", agentCode);
    }

    @PostMapping("/agents/{agentCode}/commands")
    public Map<String, String> command(@PathVariable String agentCode, @RequestBody SimulatorProtocol.Command command,
                                       HttpServletRequest request) {
        authenticate(request);
        if (!agentCode.equals(runtime.agentCode())) throw new ResponseStatusException(HttpStatus.CONFLICT, "设备尚未绑定该代理");
        if (!runtime.isOnline() && !"TASK_CANCEL".equals(command.commandType())) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "仿真体已停止，不能接收业务命令");
        }
        try { runtime.accept(command); }
        catch (IllegalArgumentException ex) { throw new ResponseStatusException(HttpStatus.BAD_REQUEST, ex.getMessage()); }
        catch (IllegalStateException ex) { throw new ResponseStatusException(HttpStatus.CONFLICT, ex.getMessage()); }
        return Map.of("status", "RECEIVED", "commandId", command.commandId());
    }

    /** Local-only operator endpoint for repeatable P2 stop/recovery verification. */
    @PostMapping("/agents/{agentCode}/capability-test")
    public Map<String, Object> testCapability(@PathVariable String agentCode,
            @RequestBody Map<String, Object> body, HttpServletRequest request) {
        authenticate(request);
        if (!agentCode.equals(runtime.agentCode())) throw new ResponseStatusException(HttpStatus.CONFLICT, "设备未绑定该代理");
        return runtime.testCapability(body);
    }

    @PostMapping("/control/online")
    public Map<String, String> online(@RequestParam boolean value, HttpServletRequest request) {
        authenticate(request);
        runtime.setOnline(value);
        return Map.of("onlineStatus", value ? "ONLINE" : "OFFLINE");
    }

    @PostMapping("/control/scenario")
    public Map<String, String> scenario(@RequestBody Map<String, String> requestBody, HttpServletRequest request) {
        authenticate(request);
        String value = requestBody.get("scenarioResult");
        try { runtime.setScenarioResult(value); }
        catch (IllegalArgumentException ex) { throw new ResponseStatusException(HttpStatus.BAD_REQUEST, ex.getMessage()); }
        return Map.of("scenarioResult", value);
    }

    @PostMapping("/control/heartbeat")
    public Map<String,Boolean> heartbeat(@RequestParam boolean value, HttpServletRequest request) {
        authenticate(request); runtime.setHeartbeatEnabled(value); return Map.of("heartbeatEnabled",value);
    }
    @PostMapping("/control/delay")
    public Map<String,Integer> delay(@RequestParam int milliseconds, HttpServletRequest request) {
        authenticate(request); runtime.setExecutionDelay(milliseconds); return Map.of("milliseconds",milliseconds);
    }

    private void authenticate(HttpServletRequest request) {
        String expected = runtime.token();
        String authorization = request.getHeader("Authorization");
        if (expected == null || expected.isBlank() || authorization == null
                || !authorization.equals("Bearer " + expected)) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "设备令牌无效");
        }
    }
}
