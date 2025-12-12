/**
 * TrendTemplateList - AI 추세 봇 템플릿 목록
 *
 * 템플릿 목록 표시:
 * - 로딩 상태
 * - 에러 처리
 * - 빈 상태
 * - 템플릿 카드 그리드
 */
import React, { useState, useEffect } from 'react';
import { Spin, Empty, Alert, Input, Select, Row, Col } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { trendTemplateAPI } from '../../../api/trendTemplate';
import TrendTemplateCard from './TrendTemplateCard';
import UseTrendTemplateModal from './UseTrendTemplateModal';
import './TrendTemplateList.css';

const { Option } = Select;

const TrendTemplateList = ({ availableBalance = 0, onBotCreated }) => {
    const [templates, setTemplates] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [sortBy, setSortBy] = useState('roi');

    // 모달 상태
    const [selectedTemplate, setSelectedTemplate] = useState(null);
    const [modalVisible, setModalVisible] = useState(false);

    // 템플릿 목록 로드
    useEffect(() => {
        loadTemplates();
    }, []);

    const loadTemplates = async () => {
        try {
            setLoading(true);
            setError(null);
            const response = await trendTemplateAPI.list({ limit: 50 });

            if (response.success) {
                setTemplates(response.data || []);
            } else {
                throw new Error(response.message || '템플릿을 불러오지 못했습니다');
            }
        } catch (err) {
            console.error('Failed to load trend templates:', err);
            setError(err.response?.data?.detail || err.message || '템플릿을 불러오지 못했습니다');
        } finally {
            setLoading(false);
        }
    };

    // Use 버튼 클릭
    const handleUse = (template) => {
        setSelectedTemplate(template);
        setModalVisible(true);
    };

    // 모달 닫기
    const handleModalClose = () => {
        setModalVisible(false);
        setSelectedTemplate(null);
    };

    // 봇 생성 성공
    const handleSuccess = (result) => {
        console.log('Trend bot created:', result);
        loadTemplates();
        onBotCreated?.();
    };

    // 필터링 및 정렬
    const filteredTemplates = templates
        .filter(t =>
            t.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
            t.name.toLowerCase().includes(searchTerm.toLowerCase())
        )
        .sort((a, b) => {
            switch (sortBy) {
                case 'roi':
                    return (b.backtest_roi_30d || 0) - (a.backtest_roi_30d || 0);
                case 'win_rate':
                    return (b.backtest_win_rate || 0) - (a.backtest_win_rate || 0);
                case 'users':
                    return (b.active_users || 0) - (a.active_users || 0);
                case 'risk':
                    const riskOrder = { low: 1, medium: 2, high: 3 };
                    return (riskOrder[a.risk_level] || 2) - (riskOrder[b.risk_level] || 2);
                case 'symbol':
                    return a.symbol.localeCompare(b.symbol);
                default:
                    return 0;
            }
        });

    if (loading) {
        return (
            <div className="trend-template-list-loading">
                <Spin size="large" />
                <p>AI 추세 전략을 불러오는 중...</p>
            </div>
        );
    }

    if (error) {
        return (
            <Alert
                type="error"
                message="오류"
                description={error}
                showIcon
                action={
                    <a onClick={loadTemplates}>다시 시도</a>
                }
            />
        );
    }

    return (
        <div className="trend-template-list">
            {/* 필터 바 */}
            <div className="trend-template-list-header">
                <Input
                    placeholder="심볼 또는 이름으로 검색..."
                    prefix={<SearchOutlined />}
                    value={searchTerm}
                    onChange={e => setSearchTerm(e.target.value)}
                    className="search-input"
                    allowClear
                />
                <Select
                    value={sortBy}
                    onChange={setSortBy}
                    className="sort-select"
                >
                    <Option value="roi">수익률 높은순</Option>
                    <Option value="win_rate">승률 높은순</Option>
                    <Option value="users">사용자 많은순</Option>
                    <Option value="risk">위험도 낮은순</Option>
                    <Option value="symbol">심볼 A-Z</Option>
                </Select>
            </div>

            {/* 템플릿 카드 그리드 */}
            {filteredTemplates.length === 0 ? (
                <Empty
                    description="등록된 AI 추세 템플릿이 없습니다"
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                />
            ) : (
                <Row gutter={[16, 16]}>
                    {filteredTemplates.map(template => (
                        <Col key={template.id} xs={24} sm={24} md={12} lg={8} xl={8}>
                            <TrendTemplateCard
                                template={template}
                                onUse={handleUse}
                            />
                        </Col>
                    ))}
                </Row>
            )}

            {/* Use 모달 */}
            <UseTrendTemplateModal
                visible={modalVisible}
                template={selectedTemplate}
                onClose={handleModalClose}
                onSuccess={handleSuccess}
                availableBalance={availableBalance}
            />
        </div>
    );
};

export default TrendTemplateList;
