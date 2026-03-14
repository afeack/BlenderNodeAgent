// frontend/src/utils/converter.ts
import { layoutNodes, optimizeLayout } from './layout';
import blenderNodesDB from '../../../backend/data/blender_nodes_db.json';

export const convertBlenderToFlow = (blenderData: any) => {
  console.log('🔄 convertBlenderToFlow called with:', blenderData);
  
  if (!blenderData) {
    console.warn('🔄 blenderData is null or undefined');
    return { nodes: [], edges: [] };
  }
  
  if (!blenderData.nodes) {
    console.warn('🔄 blenderData.nodes is missing. Available keys:', Object.keys(blenderData));
    return { nodes: [], edges: [] };
  }
  
  console.log('🔄 Processing nodes:', blenderData.nodes.length, 'connections:', blenderData.connections?.length || 0);

  // 使用新的布局算法
  const positionedNodes = layoutNodes(blenderData);
  const optimizedNodes = optimizeLayout(positionedNodes, blenderData.nodes);
  
  // 创建节点映射
  const nodeMap = new Map();
  blenderData.nodes.forEach((node: any) => {
    nodeMap.set(node.node_id, node);
  });

  // 从blender_nodes_db.json中获取节点模板
  const getNodeTemplate = (nodeType: string) => {
    return blenderNodesDB.find((template: any) => template.node_type === nodeType);
  };

  const nodes = optimizedNodes.map((positionedNode: any) => {
    const node = nodeMap.get(positionedNode.id);
    if (!node) return null;
    
    // 获取节点模板
    const nodeTemplate = getNodeTemplate(node.node_type);
    
    // 使用模板中的输入输出端口，如果没有模板则使用节点数据中的
    const inputs = nodeTemplate?.inputs || node.inputs || [];
    const outputs = nodeTemplate?.outputs || node.outputs || [];
    
    return {
      id: node.node_id,
      type: 'blenderNode', // 使用自定义节点类型
      data: { 
        label: node.node_type,
        nodeType: node.node_type,
        inputs: inputs,
        outputs: outputs,
        properties: node.properties || []
      },
      // 使用计算的位置
      position: { x: positionedNode.x, y: positionedNode.y },
      style: {
        width: 'auto',
        minWidth: '200px'
      }
    };
  }).filter(Boolean);

  const edges = blenderData.connections.map((conn: any, index: number) => ({
    id: `e-${index}`,
    source: conn.from_node,
    target: conn.to_node,
    sourceHandle: conn.from_socket,
    targetHandle: conn.to_socket,
    animated: true,
    style: { 
      stroke: '#666',
      strokeWidth: 2
    },
    // 移除连接线上的标签，因为端口名称已经在节点上显示了
  }));

  return { nodes, edges };
};

export const copyToBlenderClipboard = (blenderData: any) => {
  if (!blenderData || !blenderData.nodes) {
    alert("❌ 没有可导出的材质数据");
    return;
  }

  // 1. 封装剪贴板协议包
  const clipboardPayload = {
    protocol: "BLENDER_NODE_AGENT",
    version: "2.0",
    timestamp: Date.now(),
    material_data: blenderData
  };

  // 2. 序列化并写入剪贴板
  const jsonString = JSON.stringify(clipboardPayload, null, 2);
  
  navigator.clipboard.writeText(jsonString).then(() => {
    console.log("✅ 材质 JSON 已写入剪贴板");
    // 这里可以触发一个全局提示 UI
  }).catch(err => {
    console.error('无法复制到剪贴板', err);
    alert("复制失败，请检查浏览器权限");
  });
};