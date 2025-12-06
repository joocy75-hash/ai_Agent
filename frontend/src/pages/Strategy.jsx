import { useState } from 'react';
import { Row, Col, Typography, Tabs } from 'antd';
import { RocketOutlined, ThunderboltOutlined, EditOutlined } from '@ant-design/icons';
import StrategyList from '../components/strategy/StrategyList';
import StrategyEditor from '../components/strategy/StrategyEditor';
import SimpleStrategyCreator from '../components/strategy/SimpleStrategyCreator';

const { Title } = Typography;

export default function Strategy() {
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
    setActiveTab('list');
    setEditingStrategy(null);
  };

  const handleCancelEdit = () => {
    setActiveTab('list');
    setEditingStrategy(null);
  };

  // 간단 전략 생성 완료 시
  const handleSimpleStrategyCreated = (strategy) => {
    setActiveTab('list');
  };

  return (
    <div style={{ padding: 24 }}>
      {/* 페이지 헤더 */}
      <div style={{ marginBottom: 24 }}>
        <Title level={2}>
          <RocketOutlined style={{ marginRight: 12 }} />
          전략 관리
        </Title>
        <p style={{ color: '#888', margin: 0 }}>
          나만의 트레이딩 전략을 만들고 관리하세요
        </p>
      </div>

      {/* 탭 메뉴 */}
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            size="large"
            items={[
              {
                key: 'simple',
                label: (
                  <span>
                    <ThunderboltOutlined />
                    🌟 간단 전략 만들기
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
                label: (
                  <span>
                    <EditOutlined />
                    고급 전략 편집
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
