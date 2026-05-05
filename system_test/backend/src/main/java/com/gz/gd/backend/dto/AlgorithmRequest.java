package com.gz.gd.backend.dto;

import lombok.Data;
import java.util.List;
import java.util.Map;

@Data
public class AlgorithmRequest {
    private List<DepotDTO> depots;
    private List<CustomerDTO> customers;
    private Map<String, Object> params;
    
    @Data
    public static class DepotDTO {
        private Integer id;
        private Double x;
        private Double y;
        private Integer vehicles;
        private Integer capacity;
        private Double maxDistance;
    }
    
    @Data
    public static class CustomerDTO {
        private Integer id;
        private Double x;
        private Double y;
        private Integer demand;
    }
}
