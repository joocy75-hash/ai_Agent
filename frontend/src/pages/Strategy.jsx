import { useState, useEffect } from 'react';
import { Row, Col, Typography } from 'antd';
import { RocketOutlined } from '@ant-design/icons';
import StrategyList from '../components/strategy/StrategyList';

const { Title } = Typography;

export default function Strategy() {
  // 모바일 감지
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return (
    <div style={{ maxWidth: 1400, margin: '0 auto' }}>
      {/* 페이지 헤더 */}
      <div style={{ marginBottom: isMobile ? 12 : 24 }}>
        <Title level={isMobile ? 3 : 2}>
          <RocketOutlined style={{ marginRight: 8 }} />
          전략 관리
        </Title>
        {!isMobile && (
          <p style={{ color: '#888', margin: 0 }}>
            등록된 트레이딩 전략을 확인하고 관리하세요
          </p>
        )}
      </div>

      {/* 전략 목록 */}
      <Row gutter={isMobile ? [8, 8] : [16, 16]}>
        <Col span={24}>
          <StrategyList
            onEdit={() => {}}
            onNew={() => {}}
          />
        </Col>
      </Row>
    </div>
  );
}
