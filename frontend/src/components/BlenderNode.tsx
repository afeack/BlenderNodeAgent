import React from 'react';
import { Handle, Position } from 'reactflow';

interface BlenderNodeProps {
  data: {
    label: string;
    nodeType: string;
    inputs: Array<{ name: string; type: string; default_value?: any }>;
    outputs: Array<{ name: string; type: string }>;
    properties?: Array<{ name: string; value: any }>;
  };
}

const BlenderNode: React.FC<BlenderNodeProps> = ({ data }) => {
  const { label, nodeType, inputs, outputs, properties } = data;

  // 端口类型颜色映射
  const getPortColor = (type: string) => {
    const colorMap: Record<string, string> = {
      'SHADER': '#4a9eff',
      'RGBA': '#ff6b6b',
      'VECTOR': '#51cf66',
      'VALUE': '#ffd43b',
      'FLOAT': '#ffd43b',
      'STRING': '#cc5de8'
    };
    return colorMap[type] || '#888';
  };

  // 简化节点类型名称
  const simplifiedType = nodeType.replace('ShaderNode', '');

  return (
    <div className="blender-node bg-[#2d2d2d] border border-[#444] rounded-lg shadow-lg overflow-hidden min-w-[280px]">
      {/* 节点头部 */}
      <div className="bg-gradient-to-r from-[#3d3d3d] to-[#4a4a4a] px-3 py-2 border-b border-[#555]">
        <div className="text-xs font-bold text-white">{simplifiedType}</div>
      </div>

      {/* 三栏布局：输入 | 设置 | 输出 */}
      <div className="flex">
        {/* 左侧：输入端口栏 */}
        <div className="w-1/3 border-r border-[#444] p-2 bg-[#282828]">
          <div className="text-[8px] text-gray-500 mb-2 font-bold uppercase">输入</div>
          <div className="flex flex-col gap-2">
            {inputs.map((input, index) => (
              <div 
                key={index} 
                className="relative bg-[#333] border border-[#444] rounded p-2 hover:border-[#555] transition-colors"
              >
                <Handle
                  type="target"
                  position={Position.Left}
                  id={input.name}
                  style={{
                    width: '8px',
                    height: '8px',
                    background: getPortColor(input.type),
                    border: '2px solid #555',
                    left: '-4px',
                    top: '50%',
                    transform: 'translateY(-50%)'
                  }}
                />
                <div className="flex items-center gap-2">
                  <div 
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: getPortColor(input.type) }}
                  />
                  <div className="text-[8px] text-gray-300">{input.name}</div>
                </div>
                <div className="text-[7px] text-gray-500 mt-1">{input.type}</div>
              </div>
            ))}
            {inputs.length === 0 && (
              <div className="text-[8px] text-gray-600 italic text-center py-2">无输入</div>
            )}
          </div>
        </div>

        {/* 中间：节点设置栏 */}
        <div className="w-1/3 border-r border-[#444] p-2 bg-[#2a2a2a]">
          <div className="text-[8px] text-gray-500 mb-2 font-bold uppercase">设置</div>
          {properties && properties.length > 0 ? (
            <div className="flex flex-col gap-2">
              {properties.map((prop, index) => (
                <div 
                  key={index} 
                  className="bg-[#333] border border-[#444] rounded p-2 hover:border-[#555] transition-colors"
                >
                  <div className="text-[7px] text-gray-400 mb-1">{prop.name}</div>
                  <div className="text-[8px] text-blue-300">
                    {Array.isArray(prop.value) 
                      ? `[${prop.value.slice(0, 3).map(v => typeof v === 'number' ? v.toFixed(2) : String(v)).join(', ')}...]` 
                      : typeof prop.value === 'number' 
                        ? prop.value.toFixed(3) 
                        : String(prop.value)}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-[8px] text-gray-600 italic text-center py-2">无设置</div>
          )}
        </div>

        {/* 右侧：输出端口栏 */}
        <div className="w-1/3 p-2 bg-[#282828]">
          <div className="text-[8px] text-gray-500 mb-2 font-bold uppercase">输出</div>
          <div className="flex flex-col gap-2">
            {outputs.map((output, index) => (
              <div 
                key={index} 
                className="relative bg-[#333] border border-[#444] rounded p-2 hover:border-[#555] transition-colors"
              >
                <Handle
                  type="source"
                  position={Position.Right}
                  id={output.name}
                  style={{
                    width: '8px',
                    height: '8px',
                    background: getPortColor(output.type),
                    border: '2px solid #555',
                    right: '-4px',
                    top: '50%',
                    transform: 'translateY(-50%)'
                  }}
                />
                <div className="flex items-center gap-2 justify-end">
                  <div className="text-[8px] text-gray-300">{output.name}</div>
                  <div 
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: getPortColor(output.type) }}
                  />
                </div>
                <div className="text-[7px] text-gray-500 mt-1 text-right">{output.type}</div>
              </div>
            ))}
            {outputs.length === 0 && (
              <div className="text-[8px] text-gray-600 italic text-center py-2">无输出</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default BlenderNode;