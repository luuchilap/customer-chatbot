# Frontend Chatbot UI

A modern, responsive web interface for the MongoDB chatbot API.

## Features

✨ **Modern Design**
- Clean, professional chat interface
- Responsive design for all devices
- Smooth animations and transitions
- Real-time typing indicators

🔧 **Functionality**
- Real-time chat with the AI assistant
- Session management and conversation reset
- Customer name customization
- Character count and input validation
- Server connection status indicator
- Error handling and loading states

🎨 **User Experience**
- Welcome modal for customer name
- Auto-scroll to latest messages
- Keyboard shortcuts (Enter to send)
- Visual feedback for all interactions

## Quick Start

1. **Start the API server** (in main directory):
```bash
& "C:\Users\ADMIN\AppData\Local\Programs\Python\Python313\python.exe" app.py
```

2. **Start the frontend server**:
```bash
python frontend_server.py
```

3. **Open your browser**:
```
http://localhost:3000
```

## Files Structure

```
frontend/
├── index.html      # Main HTML structure
├── style.css       # Complete styling
└── script.js       # JavaScript functionality
```

## Configuration

The frontend connects to the API server at `http://localhost:5000` by default. To change this, edit the `apiUrl` in `script.js`:

```javascript
constructor() {
    this.apiUrl = 'http://your-api-server:port';
    // ...
}
```

## Browser Support

- Chrome/Edge 80+
- Firefox 75+
- Safari 13+
- Mobile browsers

## Example Usage

1. Enter your name in the welcome modal
2. Ask questions like:
   - "Show me all iPhones"
   - "What's the cheapest laptop?"
   - "Find products under $100"
   - "Compare iPhone 15 with iPhone 14"

The chatbot will respond with product information from your MongoDB database.

## Development

For development, you can also serve the files using any static file server:

```bash
# Using Python's built-in server
cd frontend
python -m http.server 3000

# Using Node.js live-server
npx live-server --port=3000

# Using PHP
cd frontend
php -S localhost:3000
```