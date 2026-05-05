package com.gz.gd.backend.dto;

import lombok.Data;

@Data
public class LoginResponse {
    private String token;
    private String username;
    
    public LoginResponse(String token, String username) {
        this.token = token;
        this.username = username;
    }
}
