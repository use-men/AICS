/**
 * ToolsPage — 客服快捷工具页面
 *
 * 包含多个实用小工具：
 * - 工单统计
 * - 快捷复制
 * - 计算器
 * - 文本处理
 * - 时间戳转换
 */

import { useState } from 'react';
import { Card, Typography, Input, Button, Space, Row, Col, Tag, Divider, message } from 'antd';
import {
  CopyOutlined, CalculatorOutlined, ClockCircleOutlined,
  FileTextOutlined, ClearOutlined, SwapOutlined,
} from '@ant-design/icons';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

const ToolsPage: React.FC = () => {
  // 文本处理
  const [inputText, setInputText] = useState('');
  const [outputText, setOutputText] = useState('');

  // 时间戳转换
  const [timestamp, setTimestamp] = useState('');
  const [dateString, setDateString] = useState('');

  // 计算器
  const [calcExpression, setCalcExpression] = useState('');
  const [calcResult, setCalcResult] = useState('');

  // ---- 文本处理工具 ----

  const handleTextProcess = (type: string) => {
    if (!inputText) {
      message.warning('请输入文本');
      return;
    }
    switch (type) {
      case 'upper': setOutputText(inputText.toUpperCase()); break;
      case 'lower': setOutputText(inputText.toLowerCase()); break;
      case 'trim': setOutputText(inputText.trim()); break;
      case 'length': setOutputText(`字符数: ${inputText.length}`); break;
      case 'lines': setOutputText(`行数: ${inputText.split('\n').length}`); break;
      case 'reverse': setOutputText(inputText.split('').reverse().join('')); break;
      case 'copy': navigator.clipboard.writeText(inputText); message.success('已复制'); break;
    }
  };

  // ---- 时间戳转换 ----

  const handleTimestampConvert = (direction: 'to_date' | 'to_ts') => {
    if (direction === 'to_date' && timestamp) {
      const ts = parseInt(timestamp);
      if (!isNaN(ts)) {
        const date = new Date(ts > 1e10 ? ts : ts * 1000);
        setDateString(date.toLocaleString('zh-CN'));
      } else {
        message.error('无效的时间戳');
      }
    } else if (direction === 'to_ts' && dateString) {
      const date = new Date(dateString);
      if (!isNaN(date.getTime())) {
        setTimestamp(Math.floor(date.getTime() / 1000).toString());
      } else {
        message.error('无效的日期格式');
      }
    }
  };

  // ---- 计算器 ----

  const handleCalculate = () => {
    try {
      // 安全计算（仅允许基本运算符）
      const sanitized = calcExpression.replace(/[^0-9+\-*/().]/g, '');
      const result = Function(`"use strict"; return (${sanitized})`)();
      setCalcResult(result.toString());
    } catch {
      message.error('计算表达式无效');
    }
  };

  return (
    <div style={{ padding: 0 }}>
      <Title level={4} style={{ marginBottom: 16 }}>🛠️ 快捷工具</Title>

      <Row gutter={[16, 16]}>
        {/* 文本处理工具 */}
        <Col xs={24} lg={12}>
          <Card size="small" title={<span><FileTextOutlined /> 文本处理</span>}>
            <TextArea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="输入文本..."
              autoSize={{ minRows: 3, maxRows: 6 }}
              style={{ marginBottom: 12 }}
            />
            <Space wrap size={8}>
              <Button size="small" onClick={() => handleTextProcess('upper')}>转大写</Button>
              <Button size="small" onClick={() => handleTextProcess('lower')}>转小写</Button>
              <Button size="small" onClick={() => handleTextProcess('trim')}>去空格</Button>
              <Button size="small" onClick={() => handleTextProcess('reverse')}>反转</Button>
              <Button size="small" onClick={() => handleTextProcess('length')}>统计字符</Button>
              <Button size="small" onClick={() => handleTextProcess('lines')}>统计行数</Button>
              <Button size="small" icon={<CopyOutlined />} onClick={() => handleTextProcess('copy')}>复制</Button>
              <Button size="small" icon={<ClearOutlined />} onClick={() => { setInputText(''); setOutputText(''); }}>清空</Button>
            </Space>
            {outputText && (
              <div style={{ marginTop: 12, padding: 10, background: '#f5f5f5', borderRadius: 6 }}>
                <Text code>{outputText}</Text>
              </div>
            )}
          </Card>
        </Col>

        {/* 计算器 */}
        <Col xs={24} lg={12}>
          <Card size="small" title={<span><CalculatorOutlined /> 快捷计算器</span>}>
            <Space.Compact style={{ width: '100%' }}>
              <Input
                value={calcExpression}
                onChange={(e) => setCalcExpression(e.target.value)}
                placeholder="输入表达式，如: 100 * 365"
                onPressEnter={handleCalculate}
              />
              <Button type="primary" onClick={handleCalculate}>计算</Button>
            </Space.Compact>
            {calcResult && (
              <div style={{ marginTop: 12, padding: 10, background: '#f6ffed', borderRadius: 6, border: '1px solid #b7eb8f' }}>
                <Text strong style={{ color: '#52c41a' }}>= {calcResult}</Text>
              </div>
            )}
            <div style={{ marginTop: 8 }}>
              <Space size={4}>
                <Tag color="blue">支持运算: + - * / ( )</Tag>
              </Space>
            </div>
          </Card>
        </Col>

        {/* 时间戳转换 */}
        <Col xs={24} lg={12}>
          <Card size="small" title={<span><ClockCircleOutlined /> 时间戳转换</span>}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>时间戳 → 日期</Text>
                <Space.Compact style={{ width: '100%', marginTop: 4 }}>
                  <Input
                    value={timestamp}
                    onChange={(e) => setTimestamp(e.target.value)}
                    placeholder="输入时间戳，如: 1717833600"
                  />
                  <Button onClick={() => handleTimestampConvert('to_date')}>转换</Button>
                </Space.Compact>
                {dateString && <Text style={{ fontSize: 12, marginTop: 4, display: 'block' }}>{dateString}</Text>}
              </div>
              <Divider style={{ margin: '4px 0' }} />
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>日期 → 时间戳</Text>
                <Space.Compact style={{ width: '100%', marginTop: 4 }}>
                  <Input
                    value={dateString}
                    onChange={(e) => setDateString(e.target.value)}
                    placeholder="输入日期，如: 2024-06-08 10:00:00"
                  />
                  <Button onClick={() => handleTimestampConvert('to_ts')}>转换</Button>
                </Space.Compact>
                {timestamp && <Text style={{ fontSize: 12, marginTop: 4, display: 'block' }}>{timestamp}</Text>}
              </div>
            </div>
          </Card>
        </Col>

        {/* 常用链接 */}
        <Col xs={24} lg={12}>
          <Card size="small" title={<span><SwapOutlined /> 常用链接</span>}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {[
                { name: '知识库', url: '/cs/workbench', desc: '查看常见问题' },
                { name: '工单统计', url: '/cs/tickets', desc: '查看工单列表' },
                { name: '系统设置', url: '/cs/workbench', desc: '个人设置' },
              ].map((link) => (
                <div
                  key={link.name}
                  style={{
                    padding: '8px 12px',
                    background: '#fafafa',
                    borderRadius: 6,
                    cursor: 'pointer',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                  onClick={() => {
                    navigator.clipboard.writeText(window.location.origin + link.url);
                    message.success('链接已复制');
                  }}
                >
                  <div>
                    <Text strong style={{ fontSize: 13 }}>{link.name}</Text>
                    <Text type="secondary" style={{ fontSize: 11, marginLeft: 8 }}>{link.desc}</Text>
                  </div>
                  <CopyOutlined style={{ color: '#999' }} />
                </div>
              ))}
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default ToolsPage;
