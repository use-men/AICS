/**
 * RoleManagementPage — 角色管理
 *
 * 功能:
 * - 角色列表
 * - 创建角色
 * - 编辑角色
 * - 删除角色（内置角色不可删除）
 */

import { useState, useEffect } from 'react';
import {
  Card, Table, Button, Space, Modal, Form, Input, Tag, Typography,
  message, Popconfirm, Tooltip,
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined, TeamOutlined,
  LockOutlined, SafetyOutlined,
} from '@ant-design/icons';
import { useAppSelector } from '@/store/hooks';

const { Title, Text } = Typography;
const { TextArea } = Input;

interface Role {
  id: number;
  name: string;
  code: string;
  description: string | null;
  user_count: number;
}

const BUILTIN_ROLES = new Set(['admin', 'agent', 'user']);

const RoleManagementPage: React.FC = () => {
  const user = useAppSelector((s) => s.auth.user);
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [form] = Form.useForm();

  const fetchRoles = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch('/api/v1/roles', {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setRoles(data);
      }
    } catch (error) {
      message.error('获取角色列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchRoles(); }, []);

  const handleCreate = () => {
    setEditingRole(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (role: Role) => {
    setEditingRole(role);
    form.setFieldsValue({
      name: role.name,
      code: role.code,
      description: role.description,
    });
    setModalVisible(true);
  };

  const handleDelete = async (role: Role) => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`/api/v1/roles/${role.id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (res.ok) {
        message.success('删除成功');
        fetchRoles();
      } else {
        const data = await res.json();
        message.error(data.detail || '删除失败');
      }
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const token = localStorage.getItem('access_token');

      if (editingRole) {
        // 编辑
        const res = await fetch(`/api/v1/roles/${editingRole.id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({
            name: values.name,
            description: values.description,
          }),
        });
        if (res.ok) {
          message.success('更新成功');
          setModalVisible(false);
          fetchRoles();
        } else {
          const data = await res.json();
          message.error(data.detail || '更新失败');
        }
      } else {
        // 创建
        const res = await fetch('/api/v1/roles', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify(values),
        });
        if (res.ok) {
          message.success('创建成功');
          setModalVisible(false);
          fetchRoles();
        } else {
          const data = await res.json();
          message.error(data.detail || '创建失败');
        }
      }
    } catch (error) {
      // 表单验证失败
    }
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
    },
    {
      title: '角色名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: Role) => (
        <Space>
          {BUILTIN_ROLES.has(record.code) && (
            <LockOutlined style={{ color: '#faad14' }} />
          )}
          <Text strong>{name}</Text>
        </Space>
      ),
    },
    {
      title: '角色编码',
      dataIndex: 'code',
      key: 'code',
      render: (code: string) => (
        <Tag color={code === 'admin' ? 'red' : code === 'agent' ? 'blue' : 'green'}>
          {code}
        </Tag>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      render: (desc: string) => desc || '-',
    },
    {
      title: '用户数',
      dataIndex: 'user_count',
      key: 'user_count',
      width: 80,
      render: (count: number) => (
        <Tooltip title="该角色下的用户数量">
          <Tag icon={<TeamOutlined />}>{count}</Tag>
        </Tooltip>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: any, record: Role) => (
        <Space size={4}>
          <Tooltip title="编辑">
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          {!BUILTIN_ROLES.has(record.code) && (
            <Popconfirm
              title="确定删除此角色？"
              onConfirm={() => handleDelete(record)}
              okText="确定"
              cancelText="取消"
            >
              <Tooltip title="删除">
                <Button
                  type="text"
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                />
              </Tooltip>
            </Popconfirm>
          )}
          {BUILTIN_ROLES.has(record.code) && (
            <Tooltip title="内置角色不可删除">
              <Button
                type="text"
                size="small"
                disabled
                icon={<DeleteOutlined />}
              />
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card
        title={
          <Space>
            <SafetyOutlined />
            <span>角色管理</span>
          </Space>
        }
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            新建角色
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={roles}
          rowKey="id"
          loading={loading}
          pagination={false}
        />
      </Card>

      <Modal
        title={editingRole ? '编辑角色' : '新建角色'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        okText="确定"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="角色名称"
            rules={[{ required: true, message: '请输入角色名称' }]}
          >
            <Input placeholder="如：客服主管" disabled={editingRole ? BUILTIN_ROLES.has(editingRole.code) : false} />
          </Form.Item>
          <Form.Item
            name="code"
            label="角色编码"
            rules={[{ required: true, message: '请输入角色编码' }]}
          >
            <Input placeholder="如：cs_supervisor" disabled={!!editingRole} />
          </Form.Item>
          <Form.Item
            name="description"
            label="描述"
          >
            <TextArea rows={3} placeholder="角色描述（可选）" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default RoleManagementPage;
