import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, Box, Send, Loader2, Cpu, Copy, Sparkles, Brain, Code, CheckCircle2, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react';
import NodeCanvas from './components/NodeCanvas';
import { copyToBlenderClipboard } from './utils/converter';
import { initApiHost, WebSocketManager, chatApi, graphApi } from './services/api';

type Message = {
  role: 'user' | 'assistant';
  content: string;
  thoughts?: string[];
  isThinking?: boolean;
  timestamp?: Date;
  isStreaming?: boolean;
};

// 获取默认的 API HOST
const getDefaultApiHost = () => {
  const host = window.location.hostname || '127.0.0.1';
  return `${host}:8000`;
};

const App: React.FC = () => {
  const [input, setInput] = useState('');
  const [chat, setChat] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentNodeData, setCurrentNodeData] = useState<any>(null);
  const [isReady, setIsReady] = useState(false);  // API初始化状态
  const [expandedMessages, setExpandedMessages] = useState<Set<number>>(new Set());
  const chatRef = useRef<HTMLDivElement | null>(null);
  const wsManagerRef = useRef<WebSocketManager>(new WebSocketManager());
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const currentSessionIdRef = useRef<string>('');

  // 切换消息展开/收起状态
  const toggleMessageExpansion = (index: number) => {
    setExpandedMessages(prev => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  };

  // 初始化API配置
  useEffect(() => {
    const initConfig = async () => {
      try {
        await initApiHost();
      } catch (e) {
        console.warn(`API 配置初始化失败: ${e}`);
      } finally {
        setIsReady(true);  // 初始化完成，无论成功失败
      }
    };
    
    initConfig();
  }, []);

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [chat]);



  // 获取节点数据的函数
  const fetchNodeData = async (sessionId: string) => {
    try {
      const result = await graphApi.getGraph(sessionId);
      
      if (result && result.success && result.graph) {
        setCurrentNodeData(result.graph);
      } else {
        console.warn('获取节点数据失败:', result?.error || '未知错误');
      }
    } catch (e) {
      console.error('获取节点数据错误:', e);
    }
  };

  // WebSocket消息处理函数
  const handleWebSocketMessage = (data: any) => {
    if (data.type === 'graph_ready') {
      // 后端通知节点数据已准备好，前端去获取
      if (currentSessionIdRef.current) {
        fetchNodeData(currentSessionIdRef.current);
      }
    }
  };

  const handleSend = async () => {
    // 检查初始化完成
    if (!isReady) {
      console.warn('⏳ 后端配置初始化中，请稍候...');
      return;
    }
    
    if (!input.trim() || isLoading) return;
    const userMsg: Message = { role: 'user', content: input };
    setChat((s) => [...s, userMsg]);
    setInput('');
    setIsLoading(true);

    // 生成动态 Session ID
    const sessId = sessionStorage.getItem('blender_session_id') || 
                   `web_user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    if (!sessionStorage.getItem('blender_session_id')) {
      sessionStorage.setItem('blender_session_id', sessId);
    }
    currentSessionIdRef.current = sessId;

    // 重置节点数据，为新请求做准备
    setCurrentNodeData(null);

    // 启动 WebSocket 并等待连接建立
    wsManagerRef.current.start(sessId, handleWebSocketMessage);
    await wsManagerRef.current.waitForReady();

    // 添加AI消息占位符
    setChat((s) => [...s, { 
      role: 'assistant', 
      content: '', 
      thoughts: [], 
      isThinking: true, 
      isStreaming: true,
      timestamp: new Date()
    }]);

    // 发送聊天消息
    await chatApi.sendMessage(input, sessId, (event) => {
      if (event.type === 'thought') {
        setChat((s) => {
          const copy = [...s];
          const last = copy[copy.length - 1];
          // 防止重复的 thought 消息
          const currentThoughts = last.thoughts || [];
          if (!currentThoughts.includes(event.content)) {
            last.thoughts = [...currentThoughts, event.content];
          }
          return copy;
        });
      } else if (event.type === 'text') {
        setChat((s) => {
          const copy = [...s];
          const last = copy[copy.length - 1];
          // 直接设置内容，不累积
          last.content = event.content;
          last.isThinking = false;
          // 清除之前的打字动画定时器
          if (typingTimeoutRef.current) {
            clearTimeout(typingTimeoutRef.current);
          }
          // 设置新的定时器，3秒后停止流式动画
          typingTimeoutRef.current = setTimeout(() => {
            setChat(prev => {
              const newChat = [...prev];
              const lastMsg = newChat[newChat.length - 1];
              if (lastMsg.isStreaming) {
                lastMsg.isStreaming = false;
              }
              return newChat;
            });
          }, 3000);
          return copy;
        });
      } else if (event.type === 'done') {
        setChat((s) => {
          const copy = [...s];
          const last = copy[copy.length - 1];
          last.isThinking = false;
          last.isStreaming = false;
          // 清除打字动画定时器
          if (typingTimeoutRef.current) {
            clearTimeout(typingTimeoutRef.current);
            typingTimeoutRef.current = null;
          }
          return copy;
        });
      } else if (event.type === 'error') {
        setChat((s) => {
          const copy = [...s];
          const last = copy[copy.length - 1];
          last.content = event.content;
          last.isThinking = false;
          last.isStreaming = false;
          return copy;
        });
      }
    });

    setIsLoading(false);
  };

  // 组件卸载时清理资源
  useEffect(() => {
    return () => {
      // 清理WebSocket
      wsManagerRef.current.close();
    };
  }, []);

  return (
    <div className="flex h-screen w-screen bg-[#0f0f0f] text-gray-200 font-sans overflow-hidden">
      {/* 左侧聊天区域 */}
      <div className="w-[450px] flex flex-col border-r border-[#2a2a2a] bg-[#161616] shadow-2xl">
        {/* 顶部标题栏 */}
        <div className="p-4 border-b border-[#2a2a2a] flex items-center justify-between bg-gradient-to-r from-[#1c1c1c] to-[#232323]">
          <div className="flex items-center gap-3">
            <div className="bg-gradient-to-br from-blue-600 to-purple-600 p-2 rounded-lg shadow-lg">
              <Brain size={20} className="text-white" />
            </div>
            <div>
              <h1 className="font-bold text-sm tracking-tight text-white">Blender Node Agent</h1>
              <p className="text-xs text-gray-400">智能材质节点生成器</p>
            </div>
          </div>
          {isLoading && (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-600/20 rounded-full text-blue-400 text-xs">
              <Loader2 size={14} className="animate-spin" />
              <span>处理中...</span>
            </div>
          )}
        </div>

        {/* 聊天内容区域 */}
        <div ref={chatRef} className="flex-1 overflow-y-auto p-4 space-y-6 custom-scrollbar">
          {/* 空状态 */}
          {chat.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center px-6">
              <div className="bg-gradient-to-br from-blue-600/20 to-purple-600/20 p-6 rounded-2xl mb-6">
                <Sparkles size={48} className="text-blue-400 mx-auto" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">欢迎使用 Blender Node Agent</h3>
              <p className="text-sm text-gray-400 mb-4">描述你想要的材质效果，AI 将为你生成专业的节点图</p>
              <div className="bg-[#232323] p-3 rounded-xl text-xs text-gray-500">
                <p className="mb-2 font-medium text-gray-300">示例提示：</p>
                <p>• 金属带划痕的黑色大理石</p>
                <p>• 半透明的磨砂玻璃效果</p>
                <p>• 带有锈迹的铜质材质</p>
              </div>
            </div>
          )}

          {/* 消息列表 */}
          {chat.map((m, idx) => (
            <div key={idx} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
              {/* 用户消息 */}
              {m.role === 'user' ? (
                <div className="max-w-[85%] space-y-1">
                  <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
                    <span>你</span>
                    <span>{m.timestamp?.toLocaleTimeString()}</span>
                  </div>
                  <div className="bg-gradient-to-r from-blue-600 to-blue-700 p-4 rounded-2xl rounded-tr-none text-white text-sm shadow-lg transition-all duration-300 hover:shadow-blue-600/20">
                    {m.content}
                  </div>
                </div>
              ) : (
                /* AI 消息 */
                <div className="max-w-[90%] space-y-2">
                  <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
                    <div className="w-5 h-5 rounded-full bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center text-white text-[10px]">
                      AI
                    </div>
                    <span>Blender Node Agent</span>
                    <span>{m.timestamp?.toLocaleTimeString()}</span>
                    {m.isStreaming && (
                      <div className="flex items-center gap-1 text-blue-400">
                        <Loader2 size={12} className="animate-spin" />
                        <span>生成中...</span>
                      </div>
                    )}
                  </div>
                  
                  {/* 思考过程 */}
                  {m.thoughts && m.thoughts.length > 0 && (
                    <div className="border border-[#2a2a2a] rounded-xl bg-[#1c1c1c] overflow-hidden transition-all duration-300">
                      <button 
                        onClick={() => toggleMessageExpansion(idx)}
                        className="flex items-center justify-between w-full p-3 text-[11px] text-gray-400 font-medium hover:bg-[#232323] transition-colors"
                      >
                        <div className="flex items-center gap-2">
                          <Code size={14} />
                          <span>思考过程</span>
                          <span className="text-gray-600">({m.thoughts.length})</span>
                        </div>
                        {expandedMessages.has(idx) ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      </button>
                      {expandedMessages.has(idx) && (
                        <div className="px-4 pb-3 space-y-2 border-t border-[#2a2a2a] pt-3 bg-[#1a1a1a]">
                          {m.thoughts.map((t, i) => (
                            <div key={i} className="flex items-start gap-2 text-[11px] font-mono text-gray-400">
                              <span className="text-blue-400 mt-1">▸</span>
                              <span>{t}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                  
                  {/* AI 回复内容 */}
                  {m.content && (
                    <div className="bg-[#232323] p-4 rounded-2xl rounded-tl-none text-gray-200 text-sm shadow-lg transition-all duration-300 hover:bg-[#252525]">
                      {m.content}
                      {m.isStreaming && (
                        <span className="inline-block ml-1 animate-pulse">▌</span>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* 输入区域 */}
        <div className="p-4 bg-gradient-to-r from-[#1c1c1c] to-[#232323] border-t border-[#2a2a2a]">
          <div className="flex gap-2 bg-[#0f0f0f] p-2 rounded-xl border border-[#333] transition-all duration-300 focus-within:border-blue-600/50 focus-within:shadow-[0_0_0_1px_rgba(59,130,246,0.3)]">
            <input 
              value={input} 
              onChange={(e) => setInput(e.target.value)} 
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
              placeholder="描述你想要的材质效果..."
              className="flex-1 bg-transparent px-3 py-2 text-sm focus:outline-none"
              rows={1}
            />
            <button 
              onClick={handleSend} 
              disabled={!input.trim() || isLoading}
              className={isLoading 
                ? 'p-2 rounded-lg transition-all duration-300 bg-gray-700 text-gray-500 cursor-not-allowed'
                : 'p-2 rounded-lg transition-all duration-300 bg-gradient-to-r from-blue-600 to-blue-700 text-white hover:from-blue-700 hover:to-blue-800 shadow-md hover:shadow-blue-600/20'
              }
            >
              {isLoading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
            </button>
          </div>
          <div className="text-xs text-gray-500 mt-2 text-center">
            按 Enter 发送消息，Shift+Enter 换行
          </div>
        </div>
      </div>

      {/* 右侧节点图区域 */}
      <div className="flex-1 bg-[#0a0a0a] relative">
        {/* 顶部材质信息 */}
        <div className="absolute top-4 left-4 right-4 z-10 flex items-center justify-between bg-[#1c1c1c]/90 px-4 py-3 rounded-xl border border-[#333] backdrop-blur-sm shadow-lg">
          <div className="flex items-center gap-3">
            <div className="bg-green-500/20 p-2 rounded-lg">
              <Box size={18} className="text-green-400" />
            </div>
            <div>
              <h2 className="font-medium text-sm text-white">{currentNodeData?.material_name || 'No Material Active'}</h2>
              {currentNodeData && (
                <p className="text-xs text-gray-400">
                  {currentNodeData.nodes?.length || 0} 个节点 · {currentNodeData.connections?.length || 0} 个连接
                </p>
              )}
            </div>
          </div>
          {currentNodeData && (
            <button
              onClick={() => copyToBlenderClipboard(currentNodeData)}
              className="flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-blue-600 to-blue-700 text-white text-xs rounded-lg hover:from-blue-700 hover:to-blue-800 transition-all duration-300 shadow-md hover:shadow-blue-600/20"
              title="复制到剪贴板"
            >
              <Copy size={14} />
              <span>复制节点</span>
            </button>
          )}
        </div>
        
        {/* 节点画布 */}
        {currentNodeData ? (
          <NodeCanvas data={currentNodeData} />
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center px-6">
            <div className="bg-[#1c1c1c] p-8 rounded-2xl mb-6 border border-[#333]">
              <Box size={64} className="text-gray-600 mx-auto" />
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">等待材质生成</h3>
            <p className="text-sm text-gray-400">
              描述你想要的材质效果，AI 将为你生成节点图
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default App;
