import socketio
import asyncio
import aiohttp

# Create a Socket.IO client with specific configuration
sio = socketio.AsyncClient(
    reconnection=True,
    reconnection_attempts=5,
    reconnection_delay=1,
    reconnection_delay_max=5,
    logger=True,
    engineio_logger=True
)

@sio.event
async def connect():
    print('Connected to server')

@sio.event
async def disconnect():
    print('Disconnected from server')

@sio.event
async def message(data):
    print('Received message:', data)

async def main():
    # Create a session with specific headers
    session = aiohttp.ClientSession()
    
    # Connect to the WebSocket server with proper configuration
    try:
        await sio.connect(
            'wss://ws.testnet.kuru.io?marketAddress=0xf7f70cb1a1b1128272d1c2751ab788b1226303b1',
            transports=['websocket']
        )
        print('Successfully connected to the WebSocket server')
        
        # Keep the connection alive
        await sio.wait()
    except Exception as e:
        print(f'Error connecting to server: {e}')
    finally:
        await session.close()

if __name__ == '__main__':
    asyncio.run(main()) 