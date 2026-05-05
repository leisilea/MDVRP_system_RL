package com.gz.gd.backend.exception;

import com.gz.gd.backend.common.Result;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.validation.BindException;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;

import java.util.stream.Collectors;

/**
 * 全局异常处理器
 * 统一处理所有Controller抛出的异常，返回标准的Result格式
 */
@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {
    
    /**
     * 处理参数验证异常（@Valid注解触发）
     * 例如：@NotBlank, @Size, @Min, @Max 等验证失败
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<Void> handleValidationException(MethodArgumentNotValidException e) {
        // 获取第一个验证失败的字段错误信息
        String message = e.getBindingResult().getFieldErrors().stream()
                .map(FieldError::getDefaultMessage)
                .collect(Collectors.joining("; "));
        
        log.error("参数验证失败: {}", message);
        return Result.error(400, "参数验证失败: " + message);
    }
    
    /**
     * 处理参数绑定异常
     * 例如：表单提交时字段类型不匹配
     */
    @ExceptionHandler(BindException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<Void> handleBindException(BindException e) {
        String message = e.getBindingResult().getFieldErrors().stream()
                .map(error -> error.getField() + ": " + error.getDefaultMessage())
                .collect(Collectors.joining("; "));
        
        log.error("参数绑定失败: {}", message);
        return Result.error(400, "参数绑定失败: " + message);
    }
    
    /**
     * 处理参数类型不匹配异常
     * 例如：路径参数 /api/scenario/{id}，传入的id不是数字
     */
    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<Void> handleTypeMismatchException(MethodArgumentTypeMismatchException e) {
        String message = String.format("参数 '%s' 类型错误，期望类型: %s", 
            e.getName(), 
            e.getRequiredType() != null ? e.getRequiredType().getSimpleName() : "未知");
        
        log.error("参数类型不匹配: {}", message, e);
        return Result.error(400, message);
    }
    
    /**
     * 处理空指针异常
     * 通常是代码逻辑问题，需要修复
     */
    @ExceptionHandler(NullPointerException.class)
    @ResponseStatus(HttpStatus.INTERNAL_SERVER_ERROR)
    public Result<Void> handleNullPointerException(NullPointerException e) {
        log.error("空指针异常", e);
        return Result.error(500, "系统内部错误，请联系管理员");
    }
    
    /**
     * 处理数字格式异常
     * 例如：将非数字字符串转换为数字
     */
    @ExceptionHandler(NumberFormatException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<Void> handleNumberFormatException(NumberFormatException e) {
        log.error("数字格式错误", e);
        return Result.error(400, "数字格式错误: " + e.getMessage());
    }
    
    /**
     * 处理类型转换异常
     * 例如：JSON反序列化时类型不匹配
     */
    @ExceptionHandler(ClassCastException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<Void> handleClassCastException(ClassCastException e) {
        log.error("类型转换异常", e);
        return Result.error(400, "数据类型错误，请检查请求参数格式");
    }
    
    /**
     * 处理非法参数异常
     * 例如：业务逻辑中主动抛出的参数错误
     */
    @ExceptionHandler(IllegalArgumentException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<Void> handleIllegalArgumentException(IllegalArgumentException e) {
        log.error("非法参数: {}", e.getMessage());
        return Result.error(400, e.getMessage());
    }
    
    /**
     * 处理非法状态异常
     * 例如：业务状态不允许的操作
     */
    @ExceptionHandler(IllegalStateException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<Void> handleIllegalStateException(IllegalStateException e) {
        log.error("非法状态: {}", e.getMessage());
        return Result.error(400, e.getMessage());
    }
    
    /**
     * 处理自定义业务异常
     * 这是推荐的异常处理方式，业务逻辑中应该抛出BusinessException
     */
    @ExceptionHandler(BusinessException.class)
    public Result<Void> handleBusinessException(BusinessException e) {
        log.warn("业务异常 [{}]: {}", e.getCode(), e.getMessage());
        return Result.error(e.getCode(), e.getMessage());
    }
    
    /**
     * 处理其他运行时异常
     */
    @ExceptionHandler(RuntimeException.class)
    @ResponseStatus(HttpStatus.INTERNAL_SERVER_ERROR)
    public Result<Void> handleRuntimeException(RuntimeException e) {
        log.error("运行时异常", e);
        return Result.error(500, "系统异常: " + e.getMessage());
    }
    
    /**
     * 处理所有未捕获的异常（兜底处理）
     * 这是最后一道防线，确保所有异常都有统一的返回格式
     */
    @ExceptionHandler(Exception.class)
    @ResponseStatus(HttpStatus.INTERNAL_SERVER_ERROR)
    public Result<Void> handleException(Exception e) {
        log.error("系统异常", e);
        return Result.error(500, "系统异常: " + e.getMessage());
    }
}
