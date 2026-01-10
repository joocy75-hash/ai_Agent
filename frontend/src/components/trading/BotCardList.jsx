/**
 * BotCardList - 봇 카드 그리드 레이아웃
 * 반응형: Desktop 2열, Mobile 1열
 *
 * @param {Array} templates - 템플릿 목록
 * @param {Function} onUseTemplate - 템플릿 사용 콜백
 * @param {boolean} loading - 로딩 상태
 */

import { Card, Skeleton, Empty, Typography, Tag, Button, Space } from 'antd';
import { RobotOutlined, RiseOutlined, ThunderboltOutlined } from '@ant-design/icons';

const { Text } = Typography;

// 스켈레톤 카드 컴포넌트
const SkeletonCard = () => (
    <Card
        style={{
            borderRadius: 16,
            border: '1px solid #2d2d2d',
            background: '#1e1e1e',
        }}
        styles={{
            body: { padding: 16 }
        }}
    >
        <Skeleton
            active
            avatar={{ shape: 'square', size: 48 }}
            paragraph={{ rows: 3 }}
            title={{ width: '60%' }}
        />
    </Card>
);

// 봇 템플릿 카드 컴포넌트
const TemplateCard = ({ template, onUse }) => {
    const roiValue = template.roi || template.expected_roi || 0;
    const isPositive = roiValue >= 0;

    return (
        <Card
            style={{
                borderRadius: 16,
                border: '1px solid #2d2d2d',
                background: '#1e1e1e',
                cursor: 'pointer',
                transition: 'all 0.3s ease',
            }}
            styles={{
                body: { padding: 0 }
            }}
            hoverable
            onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = '#5856d6';
                e.currentTarget.style.boxShadow = '0 4px 20px rgba(88, 86, 214, 0.2)';
            }}
            onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = '#2d2d2d';
                e.currentTarget.style.boxShadow = 'none';
            }}
        >
            {/* Header */}
            <div style={{
                background: 'linear-gradient(135deg, #5856d6 0%, #4040b0 100%)',
                padding: '12px 16px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
            }}>
                <Space>
                    <div style={{
                        width: 36,
                        height: 36,
                        borderRadius: 10,
                        background: 'rgba(255,255,255,0.2)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: 18,
                        color: '#fff',
                    }}>
                        <ThunderboltOutlined />
                    </div>
                    <div>
                        <Text style={{ color: '#fff', fontWeight: 600, fontSize: 15, display: 'block' }}>
                            {template.name}
                        </Text>
                        <Tag style={{
                            background: 'rgba(255,255,255,0.2)',
                            border: 'none',
                            color: '#fff',
                            fontSize: 11,
                            marginTop: 2,
                        }}>
                            {template.strategy_type || 'AI Trend'}
                        </Tag>
                    </div>
                </Space>

                {/* ROI 배지 */}
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 4,
                    padding: '4px 10px',
                    background: isPositive ? 'rgba(52, 199, 89, 0.3)' : 'rgba(255, 59, 48, 0.3)',
                    borderRadius: 20,
                }}>
                    <RiseOutlined style={{ color: '#fff', fontSize: 12 }} />
                    <Text style={{ color: '#fff', fontSize: 12, fontWeight: 600 }}>
                        {isPositive ? '+' : ''}{roiValue.toFixed(1)}%
                    </Text>
                </div>
            </div>

            {/* Body */}
            <div style={{ padding: 16 }}>
                {/* 심볼 & 정보 */}
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: 12,
                }}>
                    <Tag style={{
                        background: 'rgba(0, 122, 255, 0.1)',
                        border: 'none',
                        color: '#007aff',
                        fontWeight: 600,
                        fontSize: 13,
                    }}>
                        {template.symbol || 'ETHUSDT'}
                    </Tag>
                    <Text style={{ color: '#86868b', fontSize: 12 }}>
                        {template.users_count || 0} users
                    </Text>
                </div>

                {/* 설명 */}
                <Text style={{
                    color: '#a1a1a1',
                    fontSize: 13,
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden',
                    lineHeight: '1.5',
                    marginBottom: 16,
                }}>
                    {template.description || 'AI 기반 자동 매매 전략'}
                </Text>

                {/* 통계 그리드 */}
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(3, 1fr)',
                    gap: 8,
                    marginBottom: 16,
                }}>
                    <div style={{
                        background: '#252525',
                        borderRadius: 8,
                        padding: '8px 6px',
                        textAlign: 'center',
                    }}>
                        <Text style={{ color: '#86868b', fontSize: 10, display: 'block' }}>
                            Win Rate
                        </Text>
                        <Text style={{ color: '#34c759', fontSize: 14, fontWeight: 600 }}>
                            {template.win_rate || 0}%
                        </Text>
                    </div>
                    <div style={{
                        background: '#252525',
                        borderRadius: 8,
                        padding: '8px 6px',
                        textAlign: 'center',
                    }}>
                        <Text style={{ color: '#86868b', fontSize: 10, display: 'block' }}>
                            Leverage
                        </Text>
                        <Text style={{ color: '#ff9500', fontSize: 14, fontWeight: 600 }}>
                            x{template.leverage || template.max_leverage || 10}
                        </Text>
                    </div>
                    <div style={{
                        background: '#252525',
                        borderRadius: 8,
                        padding: '8px 6px',
                        textAlign: 'center',
                    }}>
                        <Text style={{ color: '#86868b', fontSize: 10, display: 'block' }}>
                            Trades
                        </Text>
                        <Text style={{ color: '#fff', fontSize: 14, fontWeight: 600 }}>
                            {template.total_trades || 0}
                        </Text>
                    </div>
                </div>

                {/* 사용하기 버튼 */}
                <Button
                    type="primary"
                    block
                    onClick={(e) => {
                        e.stopPropagation();
                        onUse?.(template);
                    }}
                    style={{
                        height: 40,
                        borderRadius: 10,
                        background: 'linear-gradient(135deg, #5856d6 0%, #4040b0 100%)',
                        border: 'none',
                        fontWeight: 600,
                        fontSize: 14,
                    }}
                >
                    Use Template
                </Button>
            </div>
        </Card>
    );
};

export default function BotCardList({
    templates = [],
    onUseTemplate,
    loading = false
}) {
    // 로딩 상태
    if (loading) {
        return (
            <div className="bot-card-grid">
                {[1, 2, 3, 4].map((i) => (
                    <SkeletonCard key={i} />
                ))}
                <style>{gridStyles}</style>
            </div>
        );
    }

    // 빈 상태
    if (!templates || templates.length === 0) {
        return (
            <Empty
                image={<RobotOutlined style={{ fontSize: 64, color: '#5856d6' }} />}
                description={
                    <span style={{ color: '#86868b' }}>
                        No bot templates available
                    </span>
                }
                style={{
                    padding: '60px 20px',
                    background: '#1e1e1e',
                    borderRadius: 16,
                    border: '1px solid #2d2d2d',
                }}
            />
        );
    }

    // 템플릿 목록
    return (
        <>
            <div className="bot-card-grid">
                {templates.map((template) => (
                    <TemplateCard
                        key={template.id || template.code}
                        template={template}
                        onUse={onUseTemplate}
                    />
                ))}
            </div>
            <style>{gridStyles}</style>
        </>
    );
}

// 그리드 스타일
const gridStyles = `
    .bot-card-grid {
        display: grid;
        gap: 16px;
        grid-template-columns: repeat(2, 1fr);
    }

    @media (max-width: 767px) {
        .bot-card-grid {
            grid-template-columns: 1fr;
        }
    }
`;
