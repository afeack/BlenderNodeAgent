// 节点布局算法 - 从输出节点反向遍历

interface Node {
  node_id: string;
  node_type: string;
  properties?: any[];
}

interface Connection {
  from_node: string;
  to_node: string;
  from_socket: string;
  to_socket: string;
}

interface BlenderData {
  nodes: Node[];
  connections: Connection[];
  material_name?: string;
}

interface PositionedNode {
  id: string;
  x: number;
  y: number;
  level: number;
}

// 从输出节点反向计算每个节点的层级
function calculateLevelsFromOutput(nodes: Node[], connections: Connection[]): Record<string, number> {
  // 创建节点ID集合，用于快速查找
  const nodeIdSet = new Set(nodes.map(n => n.node_id));
  
  // 构建反向连接图（从子节点指向父节点）
  const parentMap: Record<string, string[]> = {};
  
  // 初始化
  nodes.forEach(node => {
    parentMap[node.node_id] = [];
  });
  
  // 构建反向连接：对于每个连接，to_node 的父节点是 from_node
  connections.forEach(conn => {
    // 只添加实际存在的节点
    if (nodeIdSet.has(conn.to_node) && nodeIdSet.has(conn.from_node)) {
      if (!parentMap[conn.to_node]) {
        parentMap[conn.to_node] = [];
      }
      parentMap[conn.to_node].push(conn.from_node);
    }
  });
  
  // 找到输出节点（没有子节点的节点，即没有作为 from_node 出现的节点）
  const allFromNodes = new Set(connections.map(c => c.from_node));
  const outputNodes = nodes.filter(n => !allFromNodes.has(n.node_id));
  
  // 如果没有找到输出节点，使用最后一个节点作为输出
  const startNodes = outputNodes.length > 0 ? outputNodes : [nodes[nodes.length - 1]];
  
  const levels: Record<string, number> = {};
  const visited = new Set<string>();
  
  // 从输出节点开始反向BFS
  function calculateLevel(nodeId: string, level: number) {
    if (visited.has(nodeId)) {
      // 如果已经访问过，取最大层级
      if (levels[nodeId] < level) {
        levels[nodeId] = level;
      }
      return;
    }
    
    visited.add(nodeId);
    levels[nodeId] = level;
    
    // 递归处理父节点（输入节点）
    const parents = parentMap[nodeId] || [];
    parents.forEach((parentId, index) => {
      // 同一层级的父节点垂直分布
      calculateLevel(parentId, level + 1);
    });
  }
  
  // 从每个输出节点开始
  startNodes.forEach((outputNode, index) => {
    calculateLevel(outputNode.node_id, 0);
  });
  
  // 处理未访问的节点（孤立的节点）
  nodes.forEach(node => {
    if (!visited.has(node.node_id)) {
      levels[node.node_id] = 0;
    }
  });
  
  return levels;
}

// 布局算法 - 从输出节点反向布局
export function layoutNodes(blenderData: BlenderData): PositionedNode[] {
  console.log('📐 layoutNodes called with:', blenderData);
  
  if (!blenderData) {
    console.warn('📐 blenderData is null or undefined');
    return [];
  }
  
  if (!blenderData.nodes) {
    console.warn('📐 blenderData.nodes is missing. Available keys:', Object.keys(blenderData));
    return [];
  }
  
  if (blenderData.nodes.length === 0) {
    console.warn('📐 blenderData.nodes is empty');
    return [];
  }
  
  console.log('📐 Processing', blenderData.nodes.length, 'nodes');
  
  const { nodes, connections } = blenderData;
  
  // 创建节点ID集合，用于验证
  const nodeIdSet = new Set(nodes.map(n => n.node_id));
  
  // 过滤掉不存在的连接
  const validConnections = connections.filter(conn => 
    nodeIdSet.has(conn.from_node) && nodeIdSet.has(conn.to_node)
  );
  
  // 计算节点层级（从输出节点反向）
  const levels = calculateLevelsFromOutput(nodes, validConnections);
  
  // 按层级分组
  const levelGroups: Record<number, string[]> = {};
  let maxLevel = 0;
  
  Object.entries(levels).forEach(([nodeId, level]) => {
    if (!levelGroups[level]) {
      levelGroups[level] = [];
    }
    levelGroups[level].push(nodeId);
    if (level > maxLevel) {
      maxLevel = level;
    }
  });
  
  // 创建节点映射
  const nodeMap = new Map<string, Node>();
  nodes.forEach(node => nodeMap.set(node.node_id, node));
  
  // 布局参数
  const levelWidth = 250; // 每层之间的水平间距
  const nodeHeight = 150; // 节点高度
  const nodeSpacing = 30; // 节点之间的垂直间距
  
  const positionedNodes: PositionedNode[] = [];
  
  // 从右到左布局（输出在右，输入在左）
  // 反转层级，使输出节点在最右边
  const reversedLevels: Record<number, string[]> = {};
  Object.entries(levelGroups).forEach(([level, nodeIds]) => {
    const reversedLevel = maxLevel - parseInt(level);
    reversedLevels[reversedLevel] = nodeIds;
  });
  
  // 计算每层的位置
  Object.entries(reversedLevels).forEach(([levelStr, nodeIds]) => {
    const level = parseInt(levelStr);
    
    // 计算该层的总高度
    const totalHeight = nodeIds.length * nodeHeight + (nodeIds.length - 1) * nodeSpacing;
    const startY = -totalHeight / 2; // 居中布局
    
    nodeIds.forEach((nodeId, index) => {
      const x = level * levelWidth;
      const y = startY + index * (nodeHeight + nodeSpacing);
      
      positionedNodes.push({
        id: nodeId,
        x,
        y,
        level
      });
    });
  });
  
  return positionedNodes;
}

// 优化布局 - 根据节点类型调整
export function optimizeLayout(positionedNodes: PositionedNode[], nodes: Node[]): PositionedNode[] {
  const nodeMap = new Map<string, Node>();
  nodes.forEach(node => nodeMap.set(node.node_id, node));
  
  return positionedNodes.map(node => {
    const nodeData = nodeMap.get(node.id);
    if (!nodeData) return node;
    
    // 输出节点已经在最右边（通过反向层级计算）
    // 输入节点（纹理、颜色等）已经在最左边
    
    return node;
  });
}
