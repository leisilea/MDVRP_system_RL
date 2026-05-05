package com.gz.gd.backend.exception;

import lombok.Getter;

/**
 * 自定义业务异常
 * 用于业务逻辑中主动抛出的异常，可以携带错误码和错误信息
 * 
 * 使用示例：
 * if (scenario == null) {
 *     throw new BusinessException(404, "场景不存在");
 * }
 */
@Getter
public class BusinessException extends RuntimeException {
    
    /**
     * 错误码
     */
    private final Integer code;
    
    /**
     * 错误信息
     */
    private final String message;
    
    /**
     * 构造函数（默认错误码500）
     * @param message 错误信息
     */
    public BusinessException(String message) {
        super(message);
        this.code = 500;
        this.message = message;
    }
    
    /**
     * 构造函数（自定义错误码）
     * @param code 错误码
     * @param message 错误信息
     */
    public BusinessException(Integer code, String message) {
        super(message);
        this.code = code;
        this.message = message;
    }
    
    /**
     * 构造函数（带原始异常）
     * @param message 错误信息
     * @param cause 原始异常
     */
    public BusinessException(String message, Throwable cause) {
        super(message, cause);
        this.code = 500;
        this.message = message;
    }
    
    /**
     * 构造函数（完整参数）
     * @param code 错误码
     * @param message 错误信息
     * @param cause 原始异常
     */
    public BusinessException(Integer code, String message, Throwable cause) {
        super(message, cause);
        this.code = code;
        this.message = message;
    }
}
