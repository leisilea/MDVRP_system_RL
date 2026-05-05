package com.gz.gd.backend.controller;

import com.gz.gd.backend.common.Result;
import com.gz.gd.backend.dto.LoginRequest;
import com.gz.gd.backend.dto.LoginResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;
import java.util.UUID;

@Slf4j
@RestController
@RequestMapping("/api/auth")
@CrossOrigin(origins = "*")
public class LoginController {
    
    private static final String ADMIN_USERNAME = "admin";
    private static final String ADMIN_PASSWORD = "123456";

    /**
     * 登录接口
     * POST /api/auth/login
     */
    @PostMapping("/login")
    public Result<LoginResponse> login(@RequestBody LoginRequest request) {
        log.info("登录请求: {}", request.getUsername());
        
        try {
            // 验证用户名和密码
            if (ADMIN_USERNAME.equals(request.getUsername()) && 
                ADMIN_PASSWORD.equals(request.getPassword())) {
                
                // 生成 Token（使用 UUID）
                String token = UUID.randomUUID().toString().replace("-", "");
                
                // 返回登录成功
                LoginResponse response = new LoginResponse(token, request.getUsername());
                log.info("登录成功: {}, Token: {}", request.getUsername(), token);
                
                return Result.success(response);
            } else {
                log.warn("登录失败: 用户名或密码错误");
                return Result.error("用户名或密码错误");
            }
        } catch (Exception e) {
            log.error("登录异常", e);
            return Result.error("登录异常: " + e.getMessage());
        }
    }

    /**
     * 登出接口
     * POST /api/auth/logout
     */
    @PostMapping("/logout")
    public Result<String> logout() {
        log.info("用户登出");
        return Result.success("登出成功");
    }
}
