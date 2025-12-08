import { useState, useEffect } from 'react';
import { Row, Col, Typography, Tabs } from 'antd';
import { RocketOutlined, ThunderboltOutlined, EditOutlined } from '@ant-design/icons';
import StrategyList from '../components/strategy/StrategyList';
import StrategyEditor from '../components/strategy/StrategyEditor';
import SimpleStrategyCreator from '../components/strategy/SimpleStrategyCreator';

const { Title } = Typography;

export default function Strategy() {
  // 모바일 감지
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  // 목록 새로고침 키 (전략 생성 후 목록 강제 새로고침용)
  const [refreshKey, setRefreshKey] = useState(0);

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
    // 전략 저장 후 목록으로 돌아가기
    setRefreshKey(prev => prev + 1); // 목록 새로고침 트리거
    setActiveTab('list');
    setEditingStrategy(null);
  };

  const handleCancelEdit = () => {
    setActiveTab('list');
    setEditingStrategy(null);
  };

  // 간단 전략 생성 완료 시
  const handleSimpleStrategyCreated = (strategy) => {
    console.log('[Strategy] Strategy created, refreshing list...', strategy);
    setRefreshKey(prev => prev + 1); // 목록 새로고침 트리거
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
                label: (
                  <span>
                    <RocketOutlined />
                    {isMobile ? '전략 목록' : '전략 목록'}
                  </span>
                ),
                children: (
                  <StrategyList
                    key={refreshKey} // refreshKey가 변경되면 컴포넌트 리마운트 -> loadStrategies() 자동 호출
                    onEdit={handleEditStrategy}
                    onNew={handleNewStrategy}
                  />
                )
              },
              {
                key: 'editor',
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
