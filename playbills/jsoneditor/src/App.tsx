import React from 'react';
import './App.css';
import ExcelJsonEditor from './components/ExcelJsonEditor';

const App: React.FC = () => {
  return (
    <div className="content">
      <h1 className="centered-text">演出事件元数据编辑</h1>
      <ExcelJsonEditor />
    </div>
  );
};

export default App;