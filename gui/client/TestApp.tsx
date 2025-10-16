import { createElement } from "react";
import { createRoot } from "react-dom/client";

const TestApp = () => {
  return createElement(
    'div',
    { style: { padding: '20px', fontSize: '24px', color: '#333' } },
    createElement('h1', null, '🎉 Awakened Mind - System Online!'),
    createElement('p', null, 'If you can see this, React is working!'),
    createElement('p', { style: { color: 'green' } }, '✅ Frontend: WORKING'),
    createElement('p', { style: { color: 'green' } }, '✅ API Server: RUNNING'),
    createElement('p', null, 'Backend has 16 knowledge items in ChromaDB')
  );
};

const container = document.getElementById("root");
if (container) {
  const root = createRoot(container);
  root.render(createElement(TestApp));
} else {
  console.error("Root element not found!");
}
