package com.gz.gd.backend.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.Data;
import java.util.List;
import java.util.Map;

@Data
@JsonIgnoreProperties(ignoreUnknown = true)
// 上述注解为忽视未知字段防止未来添加新字段不合适
public class AlgorithmResponse {
    private Boolean success;
    private SolutionData data;
    private String error;
    
    @Data
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class SolutionData {
        private List<RouteDTO> routes;
        private Double totalCost;
        private Double computeTime;
        private String algorithm;
        private Integer numRoutes;
        private List<Map<String, Object>> convergence;
    }
    
    @Data
    public static class RouteDTO {
        private Integer vehicleId;
        private Integer depotId;
        private List<Integer> path;
        private Double cost;
    }
}
