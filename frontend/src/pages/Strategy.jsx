import { useState, useEffect } from 'react';
import { Row, Col, Typography, Tabs } from 'antd';
import { RocketOutlined, ThunderboltOutlined, EditOutlined } from '@ant-design/icons';
import StrategyList from '../components/strategy/StrategyList';
import StrategyEditor from '../components/strategy/StrategyEditor';
import SimpleStrategyCreator from '../components/strategy/SimpleStrategyCreator';
import { useStrategies } from '../context/StrategyContext';

const { Title } = Typography;

export default function Strategy() {
  // 전역 전략 상태 관리
  const { refreshStrategies } = useStrategies();

  // 모바일 감지
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const [activeTab, setActiveTab] = useState('simple');
  const [editingStrategy, setEditingStrategy] = useState(null);

  const handleNewStrategy = () => {
    setEditingStrategy(null);
    setActiveTab('editor');
  };

  const handleEditStrategy = (strategy) => {
    setEditingStrategy(strategy);
    setActiveTab('editor');
  };

  const handleSaveStrategy = (values) => {
    // 전략 저장 후 전역 상태 새로고침 후 목록으로 돌아가기
    refreshStrategies();
    setActiveTab('list');
    setEditingStrategy(null);
  };

  const handleCancelEdit = () => {
    setActiveTab('list');
    setEditingStrategy(null);
  };

  // 간단 전략 생성 완료 시
  const handleSimpleStrategyCreated = (strategy) => {
    console.log('[Strategy] Strategy created, refreshing global list...', strategy);
    refreshStrategies(); // 전역 상태 새로고침
    setActiveTab('list');
  };

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
            나만의 트레이딩 전략을 만들고 관리하세요
          </p>
        )}
      </div>

      {/* 탭 메뉴 */}
      <Row gutter={isMobile ? [8, 8] : [16, 16]}>
        <Col span={24}>
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            size={isMobile ? 'middle' : 'large'}
            items={[
              {
                key: 'simple',
                destroyInactive: true,
                label: (
                  <span>
                    <ThunderboltOutlined />
                    {isMobile ? '간단 만들기' : '🌟 간단 전략 만들기'}
                  </span>
                ),
                children: (
                  <SimpleStrategyCreator
                    onStrategyCreated={handleSimpleStrategyCreated}
                  />
                )
              },
              {
                key: 'list',
                destroyInactive: true,
                label: (
                  <span>
                    <RocketOutlined />
                    전략 목록
                  </span>
                ),
                children: (
                  <StrategyList
                    onEdit={handleEditStrategy}
                    onNew={handleNewStrategy}
                  />
                )
              },
              {
                key: 'editor',
                destroyInactive: true,
                label: (
                  <span>
                    <EditOutlined />
                    {isMobile ? '고급 편집' : '고급 전략 편집'}
                  </span>
                ),
                children: (
                  <StrategyEditor
                    strategy={editingStrategy}
                    onSave={handleSaveStrategy}
                    onCancel={handleCancelEdit}
                  />
                )
              }
            ]}
          />
        </Col>
      </Row>
    </div>
  );
}
