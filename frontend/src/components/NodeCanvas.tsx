import React, { useMemo } from 'react';
import ReactFlow, { Background, Controls, MiniMap } from 'reactflow';
import 'reactflow/dist/style.css';
import { convertBlenderToFlow } from '../utils/converter';
import BlenderNode from './BlenderNode';

// 注册自定义节点类型
const nodeTypes = {
  blenderNode: BlenderNode,
};

const NodeCanvas = ({ data }: { data: any }) => {
  console.log('🎨 NodeCanvas received data:', data);
  
  const { nodes, edges } = useMemo(() => {
    console.log('🎨 useMemo executing with data:', data);
    const result = convertBlenderToFlow(data);
    console.log('🎨 convertBlenderToFlow result:', { nodes: result.nodes.length, edges: result.edges.length });
    return result;
  }, [data]);

  console.log('🎨 Rendering ReactFlow with:', { nodes: nodes.length, edges: edges.length });

  if (nodes.length === 0) {
    return (
      <div className="w-full h-full bg-[#151515] flex items-center justify-center">
        <div className="text-gray-400 text-center">
          <p>暂无节点数据</p>
          <p className="text-xs mt-2">请检查数据格式是否正确</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full bg-[#151515]">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        // 强制深色主题
        colorMode="dark"
      >
        <Background color="#333" gap={20} />
        <Controls />
        <MiniMap style={{ background: '#222' }} nodeColor="#444" />
      </ReactFlow>
    </div>
  );
};

export default NodeCanvas;