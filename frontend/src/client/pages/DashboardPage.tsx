import { Card, Row, Col, Typography } from 'antd';

const { Title } = Typography;

const DashboardPage: React.FC = () => (
  <div className="page-container">
    <Title level={4}>工作台</Title>
    <Row gutter={16}>
      <Col span={8}><Card title="我的工单">0</Card></Col>
      <Col span={8}><Card title="待处理">0</Card></Col>
      <Col span={8}><Card title="已解决">0</Card></Col>
    </Row>
  </div>
);

export default DashboardPage;
