import logManager
from flask import Response, stream_with_context, Blueprint, request
import json
from time import sleep, time
import HueObjects
import threading
import ssl
import socket

logging = logManager.logger.get_logger(__name__)
stream = Blueprint('stream', __name__)

# Global variables for managing connections and events
pending_events = []
event_lock = threading.Lock()
active_connections = set()
connection_lock = threading.Lock()

def messageBroker():
    """Background thread that processes events from HueObjects.eventstream and distributes them to pending_events"""
    while True:
        try:
            if len(HueObjects.eventstream) > 0:
                logging.info(f"messageBroker: Found {len(HueObjects.eventstream)} events in HueObjects.eventstream")
                # Copy events to pending_events for distribution
                with event_lock:
                    events_to_add = []
                    for event in HueObjects.eventstream:
                        events_to_add.append(event)
                        logging.info(f"Added event to pending: {event.get('type', 'unknown')}_{event.get('id', 'unknown')}")
                    
                    if events_to_add:
                        pending_events.extend(events_to_add)
                        logging.info(f"Added {len(events_to_add)} events to pending_events, total pending: {len(pending_events)}")
                    
                    # Clear the original eventstream
                    HueObjects.eventstream = []
                    logging.info("messageBroker: Cleared HueObjects.eventstream")
            else:
                # No events to process - continue silently
                pass
            
            # Process events every 10ms for immediate delivery
            sleep(0.01)
        except Exception as e:
            logging.error(f"messageBroker error: {e}")
            sleep(0.1)

@stream.route('/eventstream/clip/v2')
def streamV2Events():
    client_id = id(request)
    
    with connection_lock:
        active_connections.add(client_id)
        logging.info(f"New event stream connection established. Total connections: {len(active_connections)}")
    
    def generate():
        try:
            # Send initial connection message
            yield ": hi\n\n"
            logging.debug(f"Client {client_id}: Sent : hi")
            
            # Send keepalive every 30 seconds to maintain connection
            last_keepalive = time()
            keepalive_interval = 30
            
            # Connection health monitoring
            last_activity = time()
            max_idle_time = 300  # 5 minutes max idle time
            
            # Continuous event loop that maintains persistent connection
            while True:
                current_time = time()
                
                # Check connection health
                if current_time - last_activity > max_idle_time:
                    logging.warning(f"Client {client_id}: Connection idle for too long, closing")
                    break
                
                # Send keepalive to prevent SSL timeout
                if current_time - last_keepalive >= keepalive_interval:
                    try:
                        yield ": keepalive\n\n"
                        last_keepalive = current_time
                        last_activity = current_time
                        logging.debug(f"Client {client_id}: Sent keepalive")
                    except Exception as e:
                        logging.debug(f"Keepalive failed for client {client_id}: {e}")
                        break
                
                events_to_send = []
                
                # Get events for this client
                with event_lock:
                    if pending_events:
                        events_to_send = pending_events.copy()
                        pending_events.clear()
                        logging.info(f"Client {client_id} received {len(events_to_send)} events from pending_events")
                        last_activity = current_time  # Update activity timestamp
                    else:
                        # No events to send - continue silently
                        pass
                
                # Send events to this client (batched like original bridge)
                if events_to_send:
                    try:
                        # Create single batched message with all events (matches original bridge format)
                        timestamp = int(current_time)
                        event_message = f"id: {timestamp}:0\ndata: {json.dumps(events_to_send, separators=(',', ':'))}\n\n"
                        yield event_message
                        logging.info(f"Sent {len(events_to_send)} batched events to client {client_id}")
                        last_activity = current_time  # Update activity timestamp
                    except Exception as e:
                        # Client likely disconnected or SSL error
                        if "SSL" in str(e) or "EOF" in str(e):
                            logging.warning(f"SSL connection error for client {client_id}: {e}")
                        else:
                            logging.debug(f"Error sending batched events to client {client_id}: {e}")
                        break
                
                # Brief sleep to prevent excessive CPU usage while maintaining connection
                sleep(0.001)
                
        except ssl.SSLError as e:
            logging.warning(f"SSL error for client {client_id}: {e}")
        except socket.error as e:
            logging.warning(f"Socket error for client {client_id}: {e}")
        except Exception as e:
            logging.debug(f"Event stream error for client {client_id}: {e}")
        finally:
            with connection_lock:
                active_connections.discard(client_id)
                logging.info(f"Event stream connection closed. Total connections: {len(active_connections)}")

    return Response(
        generate(),
        mimetype='text/event-stream; charset=utf-8',
        headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Cache-Control',
            'X-Accel-Buffering': 'no',  # Disable nginx buffering
            'Transfer-Encoding': 'chunked'  # Use chunked transfer encoding
        }
    )

@stream.route('/eventstream/health')
def stream_health():
    """Health check endpoint for monitoring event stream connections"""
    with connection_lock:
        return {
            'status': 'healthy',
            'active_connections': len(active_connections),
            'timestamp': time()
        }

def get_active_connection_count():
    """Get the current number of active event stream connections"""
    with connection_lock:
        return len(active_connections)
