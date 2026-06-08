/**
 * TicketStatusSwitcher — 工单状态快捷切换组件
 *
 * 功能:
 * - 一键切换工单状态
 * - 状态流转记录
 * - 快捷操作按钮
 */

import { useState } from 'react';
import { Card, Button, Typography, Tag, Space, Steps, message as antMessage } from 'antd';
import {
  ClockCircleOutlined, PlayCircleOutlined, CheckCircleOutlined,
  CloseCircleOutlined, SwapOutlined,
} from '@ant-design/icons';

const { Text } = Typography;

// ---- 状态配置 ----

interface StatusConfig {
  key: string;
  label: string;
  color: string;
  icon: React.ReactNode;
  nextStatuses: string[];
}

const STATUS_CONFIG: Record<string, StatusConfig> = {
  pending: { key: 'pending', label: '待分配', color: 'default', icon: <ClockCircleOutlined />, nextStatuses: ['assigned'] },
  assigned: { key: 'assigned', label: '已分配', color: 'processing', icon: <PlayCircleOutlined />, nextStatuses: ['processing'] },
  processing: { key: 'processing', label: '处理中', color: 'blue', icon: <PlayCircleOutlined />, nextStatuses: ['resolved', 'closed'] },
  resolved: { key: 'resolved', label: '已解决', color: 'success', icon: <CheckCircleOutlined />, nextStatuses: ['closed', 'processing'] },
  closed: { key: 'closed', label: '已关闭', color: 'default', icon: <CloseCircleOutlined />, nextStatuses: ['processing'] },
};

// ---- Props ----

interface TicketStatusSwitcherProps {
  ticketId: number;
  currentStatus: string;
  onStatusChange?: (newStatus: string) => void;
  style?: React.CSSProperties;
}

// ---- 组件 ----

const TicketStatusSwitcher: React.FC<TicketStatusSwitcherProps> = ({
  ticketId,
  currentStatus,
  onStatusChange,
  style,
}) => {
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(currentStatus);

  const currentConfig = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
  const nextStatuses = currentConfig.nextStatuses;

  const handleStatusChange = async (newStatus: string) => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`/api/v1/tickets/${ticketId}/status`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ status: newStatus }),
      });

      if (res.ok) {
        setStatus(newStatus);
        onStatusChange?.(newStatus);
        antMessage.success(`工单状态已更新为: ${STATUS_CONFIG[newStatus]?.label}`);
      } else {
        antMessage.error('状态更新失败');
      }
    } catch (error) {
      antMessage.error('状态更新失败');
    } finally {
      setLoading(false);
    }
  };

  // 状态流转步骤
  const statusSteps = ['pending', 'assigned', 'processing', 'resolved'];
  const currentStepIndex = statusSteps.indexOf(status);

  return (
    <div style={style}>
      {/* 当前状态 */}
      <div style={{ marginBottom: 8, textAlign: 'center' }}>
        <Tag
          color={currentConfig.color}
          icon={currentConfig.icon}
          style={{ fontSize: 12, padding: '2px 8px', borderRadius: 10 }}
        >
          {currentConfig.label}
        </Tag>
      </div>

      {/* 状态流转进度 */}
      <Steps
        size="small"
        current={currentStepIndex >= 0 ? currentStepIndex : 0}
        items={statusSteps.map((s) => ({
          title: <span style={{ fontSize: 10 }}>{STATUS_CONFIG[s]?.label}</span>,
          status: s === status ? 'process' : statusSteps.indexOf(s) < currentStepIndex ? 'finish' : 'wait',
        }))}
        style={{ marginBottom: 8 }}
      />

      {/* 快捷操作按钮 */}
      <div style={{ display: 'flex', gap: 6 }}>
        {nextStatuses.map((nextStatus) => {
          const config = STATUS_CONFIG[nextStatus];
          const isResolve = nextStatus === 'resolved';
          const isClose = nextStatus === 'closed';
          const isProcessing = nextStatus === 'processing';

          return (
            <Button
              key={nextStatus}
              type={isResolve ? 'primary' : 'default'}
              danger={isClose}
              icon={config.icon}
              onClick={() => handleStatusChange(nextStatus)}
              loading={loading}
              size="small"
              style={{
                flex: 1,
                borderColor: isProcessing ? '#1890ff' : undefined,
                color: isProcessing ? '#1890ff' : undefined,
                borderRadius: 4,
                fontSize: 11,
              }}
            >
              {isResolve ? '已解决' : isClose ? '关闭' : isProcessing ? '处理' : config.label}
            </Button>
          );
        })}
      </div>
    </div>
  );
};

export default TicketStatusSwitcher;
