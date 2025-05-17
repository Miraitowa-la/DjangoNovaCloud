#!/usr/bin/env python
"""
TCP服务器启动脚本

使用方法:
python run_tcp_server.py

此脚本会启动一个TCP服务器，监听9000端口，处理设备连接。
"""

import os
import sys
import django
import argparse
import logging
from typing import Dict, Any, Optional, Callable
import asyncio

# 设置Django环境
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DjangoNovaCloud.settings')
django.setup()

# 导入消费者类
from tcp_server.consumers import TCPDeviceConsumer

# 从settings获取TCP配置
from django.conf import settings

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("tcp_server")


class TCPServer:
    """TCP服务器类"""
    
    def __init__(self, host: str, port: int):
        """初始化TCP服务器"""
        self.host = host
        self.port = port
        self.server = None
        self.clients = {}  # 客户端连接映射
    
    async def start_server(self):
        """启动TCP服务器"""
        try:
            # 创建TCP服务器
            self.server = await asyncio.start_server(
                self.handle_client,
                self.host,
                self.port
            )
            
            addr = self.server.sockets[0].getsockname()
            logger.info(f'TCP服务器开始运行在 {addr}')
            
            # 保持服务器运行
            async with self.server:
                await self.server.serve_forever()
        
        except Exception as e:
            logger.exception(f"启动TCP服务器时出错: {str(e)}")
            sys.exit(1)
    
    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """处理客户端连接"""
        # 获取客户端地址
        addr = writer.get_extra_info('peername')
        client_id = f"{addr[0]}:{addr[1]}"
        logger.info(f"新的客户端连接: {client_id}")
        
        # 创建消费者实例
        consumer = TCPDeviceConsumer()
        
        # 设置消费者作用域
        scope = {
            "type": "tcp",
            "client": addr,
            "server": (self.host, self.port),
        }
        consumer.scope = scope
        
        # 创建发送函数
        async def send(message: Dict[str, Any]):
            """发送消息到客户端"""
            if message["type"] == "tcp.send":
                writer.write(message["data"])
                await writer.drain()
            elif message["type"] == "tcp.close":
                writer.close()
                await writer.wait_closed()
        
        # 设置消费者的发送函数
        consumer.send = send
        
        # 调用连接事件
        await consumer.tcp_connect({"type": "tcp.connect"})
        
        # 保存客户端连接
        self.clients[client_id] = {"consumer": consumer, "writer": writer}
        
        try:
            # 读取数据循环
            while True:
                # 读取数据，最大1KB
                data = await reader.read(1024)
                
                if not data:
                    # 连接关闭
                    logger.info(f"客户端断开连接: {client_id}")
                    await consumer.tcp_disconnect({"type": "tcp.disconnect", "code": "client_closed"})
                    break
                
                # 处理接收到的数据
                await consumer.tcp_receive({"type": "tcp.receive", "data": data})
        
        except ConnectionError:
            logger.info(f"客户端连接断开: {client_id}")
        
        except asyncio.CancelledError:
            logger.info(f"客户端连接被取消: {client_id}")
        
        except Exception as e:
            logger.exception(f"处理客户端数据时出错: {str(e)}")
        
        finally:
            # 关闭客户端连接
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            
            # 从客户端列表中移除
            self.clients.pop(client_id, None)
            logger.info(f"客户端连接已关闭: {client_id}")
    
    def stop(self):
        """停止TCP服务器"""
        if self.server:
            self.server.close()
            logger.info("TCP服务器已停止")


async def main(host: str, port: int):
    """主函数"""
    server = TCPServer(host, port)
    
    # 优雅处理Ctrl+C
    try:
        await server.start_server()
    except KeyboardInterrupt:
        logger.info("接收到终止信号，正在停止服务器...")
        server.stop()


if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='NovaCloud TCP服务器')
    
    # 获取设置中的默认值
    default_host = settings.TCP_SERVER_CONFIG.get('HOST', '0.0.0.0')
    default_port = settings.TCP_SERVER_CONFIG.get('PORT', 9000)
    
    parser.add_argument('--host', default=default_host, help='服务器绑定地址')
    parser.add_argument('--port', type=int, default=default_port, help='服务器端口')
    
    args = parser.parse_args()
    
    # 启动TCP服务器
    try:
        asyncio.run(main(args.host, args.port))
    except KeyboardInterrupt:
        logger.info("接收到终止信号，TCP服务器已停止")
        sys.exit(0) 