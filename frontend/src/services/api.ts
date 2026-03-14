// API服务模块

// 获取默认的 API HOST
const getDefaultApiHost = () => {
  const host = window.location.hostname || '127.0.0.1';
  return `${host}:8000`;
};

let apiHost = getDefaultApiHost();

// 初始化API配置
export const initApiHost = async () => {
  try {
    const response = await fetch(`http://${getDefaultApiHost()}/api/config`);
    if (response.ok) {
      const config = await response.json();
      apiHost = `${config.server_host}:${config.server_port}`;
      console.log(`✅ API Host 配置: ${apiHost}`);
    }
  } catch (e) {
    console.warn(`⚠️ 无法获取 API 配置，使用默认值: ${apiHost}`);
  }
};

// WebSocket管理类
export class WebSocketManager {
  private ws: WebSocket | null = null;
  private sessionId: string = '';
  private messageHandler: ((data: any) => void) | null = null;
  private isReady: boolean = false;
  private readyPromise: Promise<void> | null = null;
  private readyResolve: (() => void) | null = null;

  start(sessionId: string, onMessage: (data: any) => void) {
    // 如果已有连接，先关闭
    this.close();
    
    this.sessionId = sessionId;
    this.messageHandler = onMessage;
    this.isReady = false;
    
    // 创建新的Promise用于等待连接就绪
    this.readyPromise = new Promise((resolve) => {
      this.readyResolve = resolve;
    });

    const wsUrl = `ws://${apiHost}/ws/${sessionId}`;
    console.log(`🔌 连接 WebSocket: ${wsUrl}`);
    
    try {
      this.ws = new WebSocket(wsUrl);
      
      this.ws.onopen = () => {
        console.log(`✅ WebSocket 连接成功 (session: ${sessionId})`);
        this.isReady = true;
        if (this.readyResolve) {
          this.readyResolve();
        }
      };
      
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('📡 WebSocket 收到消息:', data);
          if (this.messageHandler) {
            this.messageHandler(data);
          }
        } catch (e) {
          console.error('📡 WebSocket 消息解析错误:', e);
        }
      };
      
      this.ws.onerror = (error) => {
        console.error('📡 WebSocket 错误:', error);
      };
      
      this.ws.onclose = () => {
        console.log(`🔌 WebSocket 连接关闭 (session: ${sessionId})`);
        this.isReady = false;
      };
    } catch (e) {
      console.error('📡 WebSocket 连接失败:', e);
    }
  }

  async waitForReady(): Promise<void> {
    if (this.isReady) {
      return Promise.resolve();
    }
    if (this.readyPromise) {
      return this.readyPromise;
    }
    return Promise.resolve();
  }

  close() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.isReady = false;
    this.readyPromise = null;
    this.readyResolve = null;
  }
}

// 聊天API
export const chatApi = {
  sendMessage: async (
    message: string, 
    sessionId: string, 
    onEvent: (event: { type: string; content?: string; data?: any }) => void
  ) => {
    const url = `http://${apiHost}/api/chat`;
    
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream'
        },
        mode: 'cors',
        credentials: 'omit',
        body: JSON.stringify({
          message,
          session_id: sessionId
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('无法获取响应流');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              onEvent(data);
            } catch (e) {
              console.error('解析SSE数据失败:', line, e);
            }
          }
        }
      }

      // 处理剩余的buffer
      if (buffer.startsWith('data: ')) {
        try {
          const data = JSON.parse(buffer.slice(6));
          onEvent(data);
        } catch (e) {
          console.error('解析最后的SSE数据失败:', buffer, e);
        }
      }

    } catch (error) {
      console.error('发送消息失败:', error);
      onEvent({ type: 'error', content: '网络连接失败，请检查后端服务是否运行' });
    }
  }
};

// 节点图API
export const graphApi = {
  getGraph: async (sessionId: string) => {
    try {
      const response = await fetch(`http://${apiHost}/api/graph/${sessionId}`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json'
        },
        mode: 'cors',
        credentials: 'omit'
      });

      if (response.ok) {
        return await response.json();
      } else {
        console.error(`获取节点图失败: ${response.status}`);
        return null;
      }
    } catch (e) {
      console.error('获取节点图错误:', e);
      return null;
    }
  }
};
