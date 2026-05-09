# MapView 组件使用分析

## 📍 **MapView 组件位置**

**组件文件**: `system_test/frontend/src/components/MapView.vue`

---

## 🔍 **MapView 被使用的位置**

### **1. MapVisualization.vue (地图可视化页面)**

**文件路径**: `system_test/frontend/src/views/MapVisualization.vue`

#### **导入方式**
```vue
<script setup>
import MapView from '@/components/MapView.vue'

const mapRef = ref(null)
</script>
```

#### **使用方式**
```vue
<template>
  <div class="map-visualization">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>地图可视化</span>
          <el-button type="primary" @click="loadTestData">
            加载测试数据
          </el-button>
        </div>
      </template>
      <MapView ref="mapRef" />
    </el-card>
  </div>
</template>
```

#### **调用的方法**
```javascript
const loadTestData = () => {
  const testDepots = [...]
  const testCustomers = [...]
  const testRoutes = [...]
  
  // 调用 MapView 的方法
  mapRef.value.drawDepots(testDepots)
  mapRef.value.drawCustomers(testCustomers)
  mapRef.value.drawRoutes(testRoutes)
  
  ElMessage.success('测试数据加载成功！')
}
```

#### **功能说明**
- **用途**: 独立的地图可视化页面,用于测试和演示地图功能
- **特点**: 提供"加载测试数据"按钮,可以快速加载示例数据
- **数据来源**: 硬编码的测试数据(2个仓库、4个客户、2条路径)

---

### **2. AlgorithmCompute.vue (算法计算页面)**

**文件路径**: `system_test/frontend/src/views/AlgorithmCompute.vue`

#### **导入方式**
```vue
<script setup>
import MapView from '@/components/MapView.vue'

const mapViewRef = ref(null)
</script>
```

#### **使用方式**
```vue
<template>
  <el-main class="map-area">
    <div v-if="!selectedScenarioId" class="empty-state">
      <el-empty description="请先选择一个场景" />
    </div>
    <div v-else class="map-wrapper">
      <MapView ref="mapViewRef" />
    </div>
  </el-main>
</template>
```

#### **调用场景和方法**

##### **场景1: 场景选择变化时**
```javascript
const handleScenarioChange = async (scenarioId) => {
  selectedScenario.value = scenarioList.value.find(s => s.id === scenarioId)
  selectedAlgorithm.value = ''
  solution.value = null
  
  // 加载场景数据
  await loadScenarioData(scenarioId)
  
  // 在地图上显示仓库和客户
  if (mapViewRef.value) {
    mapViewRef.value.clearMap()
    mapViewRef.value.drawDepots(depotList.value)
    mapViewRef.value.drawCustomers(customerList.value)
  }
}
```

##### **场景2: 算法选择变化时**
```javascript
const handleAlgorithmChange = () => {
  solution.value = null
  if (mapViewRef.value) {
    mapViewRef.value.clearMap()
    mapViewRef.value.drawDepots(depotList.value)
    mapViewRef.value.drawCustomers(customerList.value)
  }
}
```

##### **场景3: 算法计算完成时**
```javascript
// 在轮询任务状态的代码中
if (taskData.status === 'COMPLETED') {
  runningTasks.value[index].result = taskData.result
  runningTasks.value[index].totalCost = taskData.totalCost
  runningTasks.value[index].computeTime = taskData.computeTime
  
  ElMessage.success(`任务 ${task.taskId} 计算完成！`)
  
  // 如果是当前场景的任务，显示结果
  if (task.scenarioId === selectedScenarioId.value) {
    solution.value = taskData.result
    
    // 在地图上绘制路径
    if (mapViewRef.value && solution.value.routes) {
      mapViewRef.value.clearMap()
      mapViewRef.value.drawDepots(depotList.value)
      mapViewRef.value.drawCustomers(customerList.value)
      mapViewRef.value.drawRoutes(solution.value.routes)
    }
  }
}
```

##### **场景4: 应用重规划结果时**
```javascript
const handleReplanningApply = (data) => {
  const { newRoutes, replanResult } = data
  
  // 更新解决方案
  solution.value = {
    ...solution.value,
    routes: newRoutes,
    totalCost: replanResult.cost_after,
    computeTime: replanResult.solve_time
  }
  
  // 在地图上显示新路径
  if (mapViewRef.value) {
    mapViewRef.value.clearMap()
    mapViewRef.value.drawDepots(depotList.value)
    mapViewRef.value.drawCustomers(customerList.value)
    mapViewRef.value.drawRoutes(newRoutes)
  }
  
  ElMessage.success('已应用重规划结果')
}
```

#### **功能说明**
- **用途**: 算法计算的主界面,实时显示场景数据和计算结果
- **特点**: 
  - 左侧配置面板,右侧地图显示
  - 动态加载场景数据(仓库、客户)
  - 实时显示算法计算的路径结果
  - 支持重规划功能
- **数据来源**: 
  - 从数据库加载场景数据
  - 从算法服务获取计算结果

---

## 🔗 **间接调用 MapView 的组件**

### **ReplanningDialog.vue (重规划对话框)**

**文件路径**: `system_test/frontend/src/components/ReplanningDialog.vue`

#### **注意事项**
`ReplanningDialog.vue` **不直接使用** `MapView`,而是使用了一个专门的变体:

```vue
<script setup>
import ReplanningMapView from './ReplanningMapView.vue'

const replanMapRef = ref(null)
</script>

<template>
  <ReplanningMapView 
    ref="replanMapRef"
    :depots="depots"
    :customers="customers"
    :routes="routes"
    :blocked-edges="blockedEdges"
    :new-routes="newRoutes"
    :temporary-depots="temporaryDepots"
    :vehicle-positions="vehiclePositions"
    :edge-selection-mode="edgeSelectionMode"
    @edge-selected="handleEdgeSelected"
  />
</template>
```

#### **ReplanningMapView vs MapView**
- `ReplanningMapView` 是 `MapView` 的扩展版本
- 增加了重规划特有的功能:
  - 阻塞路段选择
  - 临时仓库显示
  - 车辆位置标记
  - 新旧路径对比显示
- 可能继承或复用了 `MapView` 的部分代码

---

## 📊 **MapView 调用方法总结**

### **核心方法**

根据使用情况,`MapView` 组件应该暴露以下方法:

#### **1. clearMap()**
```javascript
mapViewRef.value.clearMap()
```
**作用**: 清空地图上的所有标记和路径

**调用时机**:
- 场景切换时
- 算法切换时
- 重新计算前
- 应用重规划结果前

---

#### **2. drawDepots(depots)**
```javascript
mapViewRef.value.drawDepots(depotList.value)
```
**作用**: 在地图上绘制仓库标记点

**参数格式**:
```javascript
[
  {
    id: 1,
    name: '仓库1',
    longitude: 113.9987,
    latitude: 22.5975,
    vehicleCount: 5,
    maxCapacity: 100
  },
  // ...
]
```

**调用时机**:
- 场景加载后
- 地图清空后重新绘制

---

#### **3. drawCustomers(customers)**
```javascript
mapViewRef.value.drawCustomers(customerList.value)
```
**作用**: 在地图上绘制客户标记点

**参数格式**:
```javascript
[
  {
    id: 1,
    name: '客户1',
    longitude: 114.0087,
    latitude: 22.6075,
    demand: 20
  },
  // ...
]
```

**调用时机**:
- 场景加载后
- 地图清空后重新绘制

---

#### **4. drawRoutes(routes)**
```javascript
mapViewRef.value.drawRoutes(solution.value.routes)
```
**作用**: 在地图上绘制配送路径线条

**参数格式**:
```javascript
[
  {
    vehicleId: 1,
    depotId: 1,
    path: [1, 2, 3],  // 客户ID序列
    cost: 150.5
  },
  // ...
]
```

**调用时机**:
- 算法计算完成后
- 应用重规划结果后

---

## 🎨 **MapView 使用模式**

### **标准使用流程**

```javascript
// 1. 清空地图
mapViewRef.value.clearMap()

// 2. 绘制仓库
mapViewRef.value.drawDepots(depotList.value)

// 3. 绘制客户
mapViewRef.value.drawCustomers(customerList.value)

// 4. 绘制路径 (可选,有计算结果时)
if (solution.value && solution.value.routes) {
  mapViewRef.value.drawRoutes(solution.value.routes)
}
```

### **使用场景分类**

#### **场景A: 只显示场景数据 (无路径)**
```javascript
mapViewRef.value.clearMap()
mapViewRef.value.drawDepots(depotList.value)
mapViewRef.value.drawCustomers(customerList.value)
```
**适用于**:
- 场景选择后
- 算法选择变化时
- 计算前的预览

#### **场景B: 显示完整解决方案 (有路径)**
```javascript
mapViewRef.value.clearMap()
mapViewRef.value.drawDepots(depotList.value)
mapViewRef.value.drawCustomers(customerList.value)
mapViewRef.value.drawRoutes(solution.value.routes)
```
**适用于**:
- 算法计算完成后
- 应用重规划结果后
- 查看历史解决方案

---

## 📁 **相关文件清单**

### **MapView 组件本身**
- `system_test/frontend/src/components/MapView.vue` - 基础地图组件

### **MapView 的变体**
- `system_test/frontend/src/components/ReplanningMapView.vue` - 重规划专用地图组件

### **直接使用 MapView 的页面**
1. `system_test/frontend/src/views/MapVisualization.vue` - 地图可视化页面
2. `system_test/frontend/src/views/AlgorithmCompute.vue` - 算法计算页面

### **间接关联的组件**
- `system_test/frontend/src/components/ReplanningDialog.vue` - 使用 ReplanningMapView

---

## 🔄 **调用关系图**

```
MapView.vue (基础地图组件)
    ↑
    ├─ 直接使用
    │   ├─ MapVisualization.vue (地图可视化页面)
    │   │   └─ 方法: drawDepots(), drawCustomers(), drawRoutes()
    │   │
    │   └─ AlgorithmCompute.vue (算法计算页面)
    │       ├─ 场景切换: clearMap() → drawDepots() → drawCustomers()
    │       ├─ 算法切换: clearMap() → drawDepots() → drawCustomers()
    │       ├─ 计算完成: clearMap() → drawDepots() → drawCustomers() → drawRoutes()
    │       └─ 重规划应用: clearMap() → drawDepots() → drawCustomers() → drawRoutes()
    │
    └─ 变体组件
        └─ ReplanningMapView.vue (重规划地图组件)
            └─ 被使用于
                └─ ReplanningDialog.vue (重规划对话框)
```

---

## 📝 **使用统计**

### **直接使用次数**: 2个文件
1. MapVisualization.vue
2. AlgorithmCompute.vue

### **方法调用频率** (在 AlgorithmCompute.vue 中)
- `clearMap()`: 4次
- `drawDepots()`: 4次
- `drawCustomers()`: 4次
- `drawRoutes()`: 2次

### **调用场景分布**
- **场景加载**: 1次 (handleScenarioChange)
- **算法切换**: 1次 (handleAlgorithmChange)
- **计算完成**: 1次 (轮询任务状态)
- **重规划应用**: 1次 (handleReplanningApply)

---

## 🎯 **MapView 的核心价值**

1. **可视化展示**: 将抽象的MDVRP问题可视化为地图上的点和线
2. **实时反馈**: 动态显示算法计算结果
3. **交互体验**: 提供直观的地理信息展示
4. **结果对比**: 支持重规划前后的路径对比
5. **可复用性**: 被多个页面和场景复用

---

## 🔍 **推荐的代码审查点**

如果要审查或优化 MapView 组件,建议关注:

1. **地图库选择**: 使用的是哪个地图库 (Leaflet, Mapbox, 高德, 百度?)
2. **性能优化**: 大量标记点和路径时的渲染性能
3. **方法暴露**: 是否通过 `defineExpose` 正确暴露方法
4. **样式定制**: 仓库、客户、路径的视觉区分
5. **交互功能**: 是否支持点击、缩放、拖拽等交互
6. **错误处理**: 坐标无效、数据缺失时的处理
7. **响应式设计**: 不同屏幕尺寸下的适配
