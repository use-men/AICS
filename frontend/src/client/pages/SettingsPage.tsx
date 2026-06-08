/**
 * 个人设置页面 — 用户头像上传、个人信息修改
 */

import { useState, useRef } from 'react';
import { Card, Avatar, Button, Form, Input, App, Typography } from 'antd';
import { UserOutlined, UploadOutlined, SaveOutlined } from '@ant-design/icons';
import { useAppSelector, useAppDispatch } from '@/store/hooks';
import { updateUserInfo } from '@/store/slices/authSlice';
import { useTheme } from '@/locales/theme';


const { Title, Text } = Typography;

const SettingsPage: React.FC = () => {
  const dispatch = useAppDispatch();
  const user = useAppSelector((s) => s.auth.user);
  const { mode } = useTheme();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [avatarUrl, setAvatarUrl] = useState(user?.avatar || '');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isDark = mode === 'dark';

  // 处理头像上传
  const handleAvatarUpload = async (file: File) => {
    // 验证文件类型
    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      message.error('仅支持 JPG/PNG/GIF/WebP 格式');
      return false;
    }

    // 验证文件大小（5MB）
    if (file.size > 5 * 1024 * 1024) {
      message.error('头像大小不能超过 5MB');
      return false;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      // 获取 Token（可能在 localStorage 或 sessionStorage）
      const tokenStorage = localStorage.getItem('token_storage');
      const token = tokenStorage === 'session'
        ? sessionStorage.getItem('access_token')
        : localStorage.getItem('access_token');
      const response = await fetch('/api/v1/upload/avatar', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '上传失败');
      }

      const result = await response.json();
      setAvatarUrl(result.url);
      message.success('头像上传成功');

      // 更新 Redux 中的用户信息
      dispatch(updateUserInfo({ avatar: result.url }));

      return false; // 阻止 Ant Design 默认上传
    } catch (error: any) {
      message.error(error.message || '头像上传失败');
      return false;
    } finally {
      setUploading(false);
    }
  };

  // 处理点击上传
  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  // 处理文件选择
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleAvatarUpload(file);
    }
    // 清空 input 以便可以重复选择同一文件
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // 保存个人信息
  const handleSave = async () => {
    setLoading(true);
    try {
      const values = form.getFieldsValue();
      console.log('表单值:', values);

      // 获取 Token
      const tokenStorage = localStorage.getItem('token_storage');
      const token = tokenStorage === 'session'
        ? sessionStorage.getItem('access_token')
        : localStorage.getItem('access_token');

      console.log('Token:', token ? '已获取' : '未获取');

      // 调用后端 API 更新用户信息
      const response = await fetch('/api/v1/auth/me', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(values),
      });

      console.log('响应状态:', response.status);

      if (!response.ok) {
        const error = await response.json();
        console.error('错误:', error);
        throw new Error(error.detail || '保存失败');
      }

      const result = await response.json();
      console.log('保存成功:', result);

      // 更新 Redux 中的用户信息
      dispatch(updateUserInfo(values));

      message.success('保存成功');
    } catch (error: any) {
      console.error('保存失败:', error);
      message.error(error.message || '保存失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 24, maxWidth: 600, margin: '0 auto' }}>
      <Title level={4}>个人设置</Title>

      {/* 头像卡片 */}
      <Card
        title="头像"
        style={{
          marginBottom: 24,
          background: isDark ? '#1e1e1e' : '#fff',
          borderColor: isDark ? '#333' : undefined,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
          <div
            style={{
              position: 'relative',
              cursor: 'pointer',
            }}
            onClick={handleUploadClick}
          >
            <Avatar
              size={100}
              src={avatarUrl}
              icon={!avatarUrl && <UserOutlined />}
              style={{
                backgroundColor: isDark ? '#333' : '#f0f0f0',
              }}
            />
            <div
              style={{
                position: 'absolute',
                bottom: 0,
                right: 0,
                background: '#667eea',
                borderRadius: '50%',
                width: 32,
                height: 32,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: `2px solid ${isDark ? '#1e1e1e' : '#fff'}`,
              }}
            >
              <UploadOutlined style={{ color: '#fff', fontSize: 14 }} />
            </div>
          </div>

          <div>
            <Text type="secondary">
              点击头像上传新图片
            </Text>
            <br />
            <Text type="secondary" style={{ fontSize: 12 }}>
              支持 JPG、PNG、GIF、WebP，最大 5MB
            </Text>
          </div>
        </div>

        {/* 隐藏的文件输入 */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/gif,image/webp"
          style={{ display: 'none' }}
          onChange={handleFileChange}
        />
      </Card>

      {/* 个人信息卡片 */}
      <Card
        title="个人信息"
        style={{
          background: isDark ? '#1e1e1e' : '#fff',
          borderColor: isDark ? '#333' : undefined,
        }}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            nickname: user?.nickname || '',
            email: user?.email || '',
            phone: user?.phone || '',
          }}
        >
          <Form.Item label="用户名">
            <Input value={user?.username} disabled />
          </Form.Item>

          <Form.Item label="昵称" name="nickname">
            <Input placeholder="请输入昵称" />
          </Form.Item>

          <Form.Item label="邮箱" name="email">
            <Input placeholder="请输入邮箱" />
          </Form.Item>

          <Form.Item label="手机号" name="phone">
            <Input placeholder="请输入手机号" disabled />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              loading={loading}
              onClick={handleSave}
              style={{ background: '#667eea', borderColor: '#667eea' }}
            >
              保存修改
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default SettingsPage;
