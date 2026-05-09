# Axios 详细说明

## 📚 **什么是 Axios?**

### 定义
**Axios** 是一个基于 Promise 的 HTTP 客户端库,用于浏览器和 Node.js 环境中发送 HTTP 请求。它是目前前端开发中最流行的 HTTP 请求库之一。

### 核心特点
1. **基于 Promise**: 支持 async/await 语法,代码更简洁
2. **浏览器和 Node.js 通用**: 同一套代码可以在不同环境运行
3. **拦截器机制**: 可以在请求或响应被处理前拦截它们
4. **自动转换 JSON**: 自动将 JavaScript 对象转换为 JSON,响应数据自动解析
5. **请求取消**: 支持取消请求
6. **超时设置**: 可以设置请求超时时间
7. **CSRF 防护**: 客户端支持防御 CSRF 攻击

---

## 🔧 **Axios 的基本使用**

### 1. 安装 Axios

```bash
# 使用 npm
npm install axios

# 使用 yarn
yarn add axios

# 使用 pnpm
pnpm install axios
```

### 2. 基本请求方式

#### **GET 请求**
```javascript
import axios from 'axios'

// 方式1: 直接使用 axios
axios.get('http://localhost:8080/api/users')
  .then(response => {
    console.log(response.data)
  })
  .catch(error => {
    console.error(error)
  })

// 方式2: 使用 async/await
async function getUsers() {
  try {
    const response = await axios.get('http://localhost:8080/api/users')
    console.log(response.data)
  } catch (error) {
    console.error(error)
  }
}

// 方式3: 带查询参数
axios.get('http://localhost:8080/api/users', {
  params: {
    page: 1,
    size: 10
  }
})
// 实际请求: http://localhost:8080/api/users?page=1&size=10
```

#### **POST 请求**
```javascript
// 发送 JSON 数据
axios.post('http://localhost:8080/api/users', {
  username: 'john',
  email: 'john@example.com'
})
  .then(response => {
    console.log(response.data)
  })
  .catch(error => {
    console.error(error)
  })

// 使用 async/await
async function createUser() {
  try {
    const response = await axios.post('http://localhost:8080/api/users', {
      username: 'john',
      email: 'john@example.com'
    })
    console.log(response.data)
  } catch (error) {
    console.error(error)
  }
}
```

#### **PUT 请求**
```javascript
// 更新数据
axios.put('http://localhost:8080/api/users/1', {
  username: 'john_updated',
  email: 'john_new@example.com'
})
```

#### **DELETE 请求**
```javascript
// 删除数据
axios.delete('http://localhost:8080/api/users/1')
```

### 3. 完整的请求配置

```javascript
axios({
  method: 'post',                          // 请求方法
  url: 'http://localhost:8080/api/users', // 请求URL
  baseURL: 'http://localhost:8080',       // 基础URL
  headers: {                               // 请求头
    'Content-Type': 'application/json',
    'Authorization': 'Bearer token123'
  },
  params: {                                // URL查询参数
    page: 1,
    size: 10
  },
  data: {                                  // 请求体数据
    username: 'john',
    email: 'john@example.com'
  },
  timeout: 5000,                           // 超时时间(毫秒)
  responseType: 'json'                     // 响应数据类型
})
```

---

## 🎯 **在你的项目中如何使用 Axios**

### 第一步: 创建 Axios 实例 (request.js)

你的项目在 `system_test/frontend/src/api/request.js` 中创建了一个配置好的 Axios 实例:

```javascript
import axios from 'axios'
import { ElMessage } from 'element-plus'

// 创建 axios 实例
const request = axios.create({
  baseURL: '/api',      // 基础URL,所有请求都会加上这个前缀
  timeout: 30000        // 超时时间: 30秒
})
```

**解释**:
- `axios.create()`: 创建一个新的 Axios 实例,可以自定义配置
- `baseURL: '/api'`: 所有请求的基础路径,例如请求 `/users` 实际会请求 `/api/users`
- `timeout: 30000`: 如果请求超过30秒没有响应,会自动取消

---

### 第二步: 配置请求拦截器

**请求拦截器**在请求发送到服务器**之前**执行:

```javascript
// 请求拦截器
request.interceptors.request.use(
  config => {
    // 从 localStorage 获取 Token
    const token = localStorage.getItem('token')
    if (token) {
      // 将 Token 添加到请求头
      config.headers['Authorization'] = token
    }
    return config  // 必须返回 config
  },
  error => {
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)
```

**作用**:
1. **自动添加认证信息**: 每次请求自动从 localStorage 读取 token 并添加到请求头
2. **统一处理**: 不需要在每个请求中手动添加 token
3. **请求前处理**: 可以在这里添加 loading 状态、修改请求参数等

**执行流程**:
```
用户发起请求 → 请求拦截器 → 添加 Token → 发送到服务器
```

---

### 第三步: 配置响应拦截器

**响应拦截器**在服务器响应到达**之后**、业务代码处理**之前**执行:

```javascript
// 响应拦截器
request.interceptors.response.use(
  response => {
    const res = response.data
    
    // 检查业务状态码
    if (res.code !== 200) {
      ElMessage.error(res.message || '请求失败')
      return Promise.reject(new Error(res.message || '请求失败'))
    }
    
    return res  // 返回数据
  },
  error => {
    console.error('响应错误:', error)
    
    // 处理 401 未授权错误
    if (error.response && error.response.status === 401) {
      ElMessage.error('登录已过期，请重新登录')
      // 清除 Token
      localStorage.removeItem('token')
      localStorage.removeItem('username')
      // 跳转到登录页
      window.location.href = '/login'
    } else {
      ElMessage.error(error.message || '网络错误')
    }
    
    return Promise.reject(error)
  }
)
```

**作用**:
1. **统一处理响应**: 检查业务状态码(code)
2. **统一错误处理**: 自动显示错误提示
3. **401 处理**: 自动跳转到登录页
4. **简化业务代码**: 业务代码只需要处理成功的情况

**执行流程**:
```
服务器响应 → 响应拦截器 → 检查状态码 → 返回给业务代码
```

---

### 第四步: 封装 API 函数

在 `system_test/frontend/src/api/` 目录下按模块封装 API:

#### **示例1: 认证相关 API (auth.js)**

```javascript
import request from './request'

// 登录
export function login(data) {
  return request({
    url: '/auth/login',
    method: 'post',
    data
  })
}

// 登出
export function logout() {
  return request({
    url: '/auth/logout',
    method: 'post'
  })
}
```

**使用方式**:
```javascript
import { login } from '@/api/auth'

// 在组件中调用
async function handleLogin() {
  try {
    const response = await login({
      username: 'admin',
      password: '123456'
    })
    console.log('登录成功:', response.data)
  } catch (error) {
    console.error('登录失败:', error)
  }
}
```

#### **示例2: 算法相关 API (algorithm.js)**

```javascript
import request from './request'

// 提交异步算法任务
export function submitAlgorithmTask(data) {
  return request({
    url: '/algorithm/submit',
    method: 'post',
    data
  })
}

// 查询任务状态
export function getTaskStatus(taskId) {
  return request({
    url: `/algorithm/task/${taskId}`,
    method: 'get'
  })
}
```

**使用方式**:
```javascript
import { submitAlgorithmTask, getTaskStatus } from '@/api/algorithm'

// 提交任务
async function startAlgorithm() {
  try {
    const response = await submitAlgorithmTask({
      scenarioId: 1,
      algorithm: 'GA',
      params: {
        populationSize: 100,
        maxIterations: 500
      }
    })
    const taskId = response.data.taskId
    console.log('任务ID:', taskId)
    
    // 轮询查询任务状态
    const timer = setInterval(async () => {
      const statusRes = await getTaskStatus(taskId)
      if (statusRes.data.status === 'COMPLETED') {
        clearInterval(timer)
        console.log('任务完成:', statusRes.data.result)
      }
    }, 2000)
  } catch (error) {
    console.error('提交失败:', error)
  }
}
```

---

## 📊 **完整的请求流程图**

```
┌─────────────────────────────────────────────────────────────┐
│                      前端发起请求                              │
│  例如: login({ username: 'admin', password: '123456' })      │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   请求拦截器 (Request Interceptor)            │
│  1. 从 localStorage 读取 token                               │
│  2. 将 token 添加到请求头: Authorization: token              │
│  3. 返回修改后的 config                                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   发送 HTTP 请求                              │
│  POST http://localhost:8080/api/auth/login                  │
│  Headers: { Authorization: 'token123' }                     │
│  Body: { username: 'admin', password: '123456' }            │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   服务器处理请求                              │
│  Spring Boot 接收请求 → 验证 → 返回响应                      │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   接收服务器响应                              │
│  { code: 200, message: "登录成功", data: { token: "..." } }  │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   响应拦截器 (Response Interceptor)           │
│  1. 检查 response.data.code 是否为 200                       │
│  2. 如果不是 200,显示错误提示并 reject                        │
│  3. 如果是 401,清除 token 并跳转登录页                       │
│  4. 返回 response.data 给业务代码                            │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   业务代码处理响应                            │
│  const response = await login(...)                          │
│  console.log(response.data.token)                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔍 **实际请求示例分析**

### 示例: 用户登录流程

#### **1. 前端代码**
```javascript
import { login } from '@/api/auth'

async function handleLogin() {
  try {
    const response = await login({
      username: 'admin',
      password: '123456'
    })
    
    // 保存 token
    localStorage.setItem('token', response.data.token)
    localStorage.setItem('username', response.data.username)
    
    // 跳转到首页
    router.push('/')
  } catch (error) {
    console.error('登录失败')
  }
}
```

#### **2. API 函数 (auth.js)**
```javascript
export function login(data) {
  return request({
    url: '/auth/login',
    method: 'post',
    data
  })
}
```

#### **3. 实际发送的 HTTP 请求**
```http
POST http://localhost:8080/api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "123456"
}
```

#### **4. 服务器响应**
```json
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "username": "admin"
  }
}
```

#### **5. 响应拦截器处理**
- 检查 `code === 200` ✅
- 返回 `response.data` 给业务代码

#### **6. 业务代码接收**
```javascript
// response 的值:
{
  code: 200,
  message: "登录成功",
  data: {
    token: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    username: "admin"
  }
}

// 可以直接访问 response.data.token
```

---

## 🎨 **Axios 的高级特性**

### 1. 并发请求

```javascript
import axios from 'axios'

// 同时发送多个请求
async function loadData() {
  try {
    const [users, posts, comments] = await Promise.all([
      axios.get('/api/users'),
      axios.get('/api/posts'),
      axios.get('/api/comments')
    ])
    
    console.log('用户:', users.data)
    console.log('文章:', posts.data)
    console.log('评论:', comments.data)
  } catch (error) {
    console.error('加载失败:', error)
  }
}
```

### 2. 请求取消

```javascript
import axios from 'axios'

const CancelToken = axios.CancelToken
let cancel

// 发送请求
axios.get('/api/users', {
  cancelToken: new CancelToken(function executor(c) {
    cancel = c
  })
})

// 取消请求
cancel('用户取消了请求')
```

### 3. 上传文件

```javascript
const formData = new FormData()
formData.append('file', file)

axios.post('/api/upload', formData, {
  headers: {
    'Content-Type': 'multipart/form-data'
  },
  onUploadProgress: (progressEvent) => {
    const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total)
    console.log(`上传进度: ${percent}%`)
  }
})
```

### 4. 下载文件

```javascript
axios.get('/api/download/file.pdf', {
  responseType: 'blob'  // 重要: 设置响应类型为 blob
})
  .then(response => {
    // 创建下载链接
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'file.pdf')
    document.body.appendChild(link)
    link.click()
    link.remove()
  })
```

---

## 🆚 **Axios vs 原生 Fetch**

| 特性 | Axios | Fetch |
|------|-------|-------|
| 浏览器支持 | 需要引入库 | 原生支持(IE不支持) |
| 自动转换JSON | ✅ 自动 | ❌ 需要手动 `.json()` |
| 请求拦截器 | ✅ 支持 | ❌ 不支持 |
| 响应拦截器 | ✅ 支持 | ❌ 不支持 |
| 超时设置 | ✅ 支持 | ❌ 需要手动实现 |
| 请求取消 | ✅ 支持 | ✅ 支持(AbortController) |
| 上传进度 | ✅ 支持 | ❌ 不支持 |
| 错误处理 | ✅ 网络错误自动reject | ❌ 只有网络错误reject |

**Axios 示例**:
```javascript
axios.get('/api/users')
  .then(response => console.log(response.data))
  .catch(error => console.error(error))
```

**Fetch 示例**:
```javascript
fetch('/api/users')
  .then(response => {
    if (!response.ok) throw new Error('请求失败')
    return response.json()
  })
  .then(data => console.log(data))
  .catch(error => console.error(error))
```

---

## 💡 **最佳实践**

### 1. 统一的错误处理
```javascript
// 在响应拦截器中统一处理
request.interceptors.response.use(
  response => response.data,
  error => {
    // 根据不同的错误码显示不同的提示
    if (error.response) {
      switch (error.response.status) {
        case 401:
          ElMessage.error('未授权,请登录')
          break
        case 403:
          ElMessage.error('拒绝访问')
          break
        case 404:
          ElMessage.error('请求的资源不存在')
          break
        case 500:
          ElMessage.error('服务器错误')
          break
        default:
          ElMessage.error('请求失败')
      }
    }
    return Promise.reject(error)
  }
)
```

### 2. 环境变量配置
```javascript
// 根据环境使用不同的 baseURL
const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000
})
```

### 3. 请求重试机制
```javascript
request.interceptors.response.use(
  response => response,
  async error => {
    const config = error.config
    
    // 如果没有配置重试次数,默认为0
    if (!config.retryCount) {
      config.retryCount = 0
    }
    
    // 如果重试次数小于3次,则重试
    if (config.retryCount < 3) {
      config.retryCount++
      console.log(`第 ${config.retryCount} 次重试`)
      return request(config)
    }
    
    return Promise.reject(error)
  }
)
```

---

## 📝 **总结**

### Axios 的核心价值
1. **简化 HTTP 请求**: 提供简洁的 API
2. **拦截器机制**: 统一处理请求和响应
3. **自动转换**: JSON 数据自动转换
4. **错误处理**: 统一的错误处理机制
5. **可扩展性**: 易于扩展和定制

### 在你的项目中
- ✅ 创建了统一的 Axios 实例 (`request.js`)
- ✅ 配置了请求拦截器(自动添加 token)
- ✅ 配置了响应拦截器(统一错误处理)
- ✅ 按模块封装了 API 函数
- ✅ 使用 async/await 简化异步代码

这种架构使得前端代码更加清晰、可维护,并且易于扩展。
