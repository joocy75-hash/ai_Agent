/**
 * 초보자 가이드 컴포넌트
 * 백테스트 용어를 쉽게 설명하고, 추천 설정을 제공합니다.
 */

import React, { useState } from 'react';
import {
    Card, Typography, Space, Button, Tag, Tooltip, Modal,
    Row, Col, Divider, Progress, Alert
} from 'antd';
import {
    QuestionCircleOutlined,
    BulbOutlined,
    SafetyCertificateOutlined,
    RocketOutlined,
    StarOutlined,
    InfoCircleOutlined,
    CheckCircleOutlined,
    WarningOutlined,
    ThunderboltOutlined,
    RiseOutlined,
    FallOutlined,
    DollarOutlined,
    PercentageOutlined,
    BarChartOutlined
} from '@ant-design/icons';

const { Text, Title, Paragraph } = Typography;

// 용어 사전
export const TERMS_DICTIONARY = {
    leverage: {
        term: '레버리지',
        icon: <PercentageOutlined />,
        simple: '내 돈을 빌려서 더 큰 돈으로 거래하는 것',
        detailed: `
            레버리지 3x는 내 돈 $100으로 $300처럼 거래하는 거에요!
            
            좋은 점: 조금 올라도 3배 이익!
            나쁜 점: 조금 내려도 3배 손실...
            
            초보자 팁: 처음엔 1x~3x만 사용하세요!
        `,
        example: '100만원 × 3x 레버리지 = 300만원처럼 거래',
        risk: 'medium'
    },
    marginMode: {
        term: '마진 모드',
        icon: <SafetyCertificateOutlined />,
        simple: '손실을 어디까지 감당할지 정하는 것',
        detailed: `
            격리(Isolated): 이 거래에 넣은 돈만 잃을 수 있어요
            교차(Cross): 계좌 전체 돈을 잃을 수 있어요
            
            초보자 팁: 반드시 '격리' 모드를 선택하세요!
        `,
        example: '격리 = 안전벨트 착용, 교차 = 안전벨트 없음',
        risk: 'high'
    },
    fundingFee: {
        term: '펀딩 피',
        icon: <DollarOutlined />,
        simple: '선물 거래에서 8시간마다 내거나 받는 수수료',
        detailed: `
            선물 포지션을 오래 유지하면 주기적으로 수수료가 발생해요.
            
            롱 포지션: 보통 펀딩 피를 내요
            숏 포지션: 보통 펀딩 피를 받아요
            
            백테스트에서 펀딩 피를 적용하면 더 현실적인 결과를 볼 수 있어요!
        `,
        example: '평균 0.01% × 하루 3번 = 연간 약 11%',
        risk: 'low'
    },
    slippage: {
        term: '슬리피지',
        icon: <ThunderboltOutlined />,
        simple: '주문한 가격과 실제 체결 가격의 차이',
        detailed: `
            급하게 사거나 팔 때 원하는 가격과 다른 가격에 체결될 수 있어요.
            
            시장가 주문: 슬리피지 많음
            지정가 주문: 슬리피지 적음
            
            백테스트에서는 보통 0.05~0.1%로 설정해요!
        `,
        example: '100원에 사려했는데 101원에 체결됨',
        risk: 'low'
    },
    winRate: {
        term: '승률',
        icon: <CheckCircleOutlined />,
        simple: '전체 거래 중 이긴 거래의 비율',
        detailed: `
            100번 거래해서 60번 이겼다면 승률 60%!
            
            주의: 승률만 높다고 좋은 게 아니에요!
            이긴 금액이 작고, 진 금액이 크면 결국 손해예요.
            
            승률 50%여도 이길 때 크게 벌면 수익!
        `,
        example: '60승 40패 = 60% 승률',
        risk: 'none'
    },
    maxDrawdown: {
        term: '최대 손실 (MDD)',
        icon: <FallOutlined />,
        simple: '테스트 기간 중 가장 크게 돈이 줄어든 순간',
        detailed: `
            투자 중 최고점에서 최저점까지 떨어진 폭이에요.
            
            MDD 10%: 100만원 → 최저 90만원까지 떨어졌음
            MDD 50%: 100만원 → 최저 50만원까지 떨어졌음
            
            MDD가 높으면 심장이 쫄깃해요... 낮을수록 안정적!
        `,
        example: 'MDD 20% = 100만원이 80만원까지 떨어질 수 있음',
        risk: 'high'
    },
    profitFactor: {
        term: 'Profit Factor',
        icon: <BarChartOutlined />,
        simple: '총 이익 ÷ 총 손실',
        detailed: `
            1보다 크면 수익! 1보다 작으면 손실!
            
            1.5 이상: 괜찮은 전략
            2.0 이상: 좋은 전략
            3.0 이상: 아주 좋은 전략
            
            Profit Factor가 2면 "1원 손해 볼 때마다 2원 벌었다"는 뜻!
        `,
        example: '총 이익 200만원 ÷ 총 손실 100만원 = PF 2.0',
        risk: 'none'
    },
    sharpeRatio: {
        term: '샤프 비율',
        icon: <RiseOutlined />,
        simple: '안정적으로 수익을 냈는지 보여주는 점수',
        detailed: `
            수익률이 같아도 롤러코스터처럼 오르락내리락하면 점수가 낮아요!
            
            0 이하: 나쁨 (손실이거나 불안정)
            1 이상: 보통
            2 이상: 좋음
            3 이상: 아주 좋음
            
            샤프가 높으면 마음 편하게 투자할 수 있어요!
        `,
        example: '수익률 30%, 변동성 10% → 샤프 3.0',
        risk: 'none'
    }
};

// 결과 점수 계산기
export const calculateScoreCard = (metrics) => {
    if (!metrics) return null;

    const totalReturn = metrics.total_return || 0;
    const winRate = metrics.win_rate || 0;
    const maxDrawdown = Math.abs(metrics.max_drawdown || 0);
    const profitFactor = metrics.profit_factor || 0;
    const sharpeRatio = metrics.sharpe_ratio || 0;

    // 안정성 점수 (MDD 기반)
    let stability = 0;
    if (maxDrawdown <= 10) stability = 5;
    else if (maxDrawdown <= 20) stability = 4;
    else if (maxDrawdown <= 30) stability = 3;
    else if (maxDrawdown <= 50) stability = 2;
    else stability = 1;

    // 수익성 점수 (수익률 + PF 기반)
    let profitability = 0;
    if (totalReturn >= 100) profitability = 5;
    else if (totalReturn >= 50) profitability = 4;
    else if (totalReturn >= 20) profitability = 3;
    else if (totalReturn >= 0) profitability = 2;
    else profitability = 1;

    // 위험도 점수 (낮을수록 좋음)
    let riskLevel = 0;
    if (maxDrawdown >= 50) riskLevel = 5;
    else if (maxDrawdown >= 30) riskLevel = 4;
    else if (maxDrawdown >= 20) riskLevel = 3;
    else if (maxDrawdown >= 10) riskLevel = 2;
    else riskLevel = 1;

    // 신뢰도 점수 (승률 + 샤프 기반)
    let reliability = 0;
    if (sharpeRatio >= 2 && winRate >= 50) reliability = 5;
    else if (sharpeRatio >= 1 && winRate >= 45) reliability = 4;
    else if (sharpeRatio >= 0.5 && winRate >= 40) reliability = 3;
    else if (sharpeRatio >= 0) reliability = 2;
    else reliability = 1;

    // 종합 평가
    const average = (stability + profitability + reliability) / 3;
    let grade = '';
    let gradeColor = '';
    let comment = '';

    if (average >= 4.5) {
        grade = 'S'; gradeColor = '#722ed1'; comment = '최고의 전략! 매우 우수합니다.';
    } else if (average >= 4) {
        grade = 'A'; gradeColor = '#52c41a'; comment = '좋은 전략! 실전 적용을 고려해볼만 합니다.';
    } else if (average >= 3) {
        grade = 'B'; gradeColor = '#1890ff'; comment = '괜찮은 전략! 조금 더 개선하면 좋겠어요.';
    } else if (average >= 2) {
        grade = 'C'; gradeColor = '#faad14'; comment = '보통 전략. 다른 설정을 시도해보세요.';
    } else {
        grade = 'D'; gradeColor = '#f5222d'; comment = '위험한 전략. 다시 검토가 필요합니다.';
    }

    return {
        stability,
        profitability,
        riskLevel,
        reliability,
        grade,
        gradeColor,
        comment,
        average
    };
};

// 용어 설명 툴팁 컴포넌트
export const TermTooltip = ({ termKey, children }) => {
    const [modalOpen, setModalOpen] = useState(false);
    const term = TERMS_DICTIONARY[termKey];

    if (!term) return children;

    return (
        <>
            <Space>
                {children}
                <Tooltip title={term.simple}>
                    <QuestionCircleOutlined
                        style={{
                            color: '#86868b',
                            cursor: 'pointer',
                            fontSize: 14
                        }}
                        onClick={() => setModalOpen(true)}
                    />
                </Tooltip>
            </Space>

            <Modal
                title={
                    <Space>
                        {term.icon}
                        <span>{term.term}이란?</span>
                    </Space>
                }
                open={modalOpen}
                onCancel={() => setModalOpen(false)}
                footer={
                    <Button type="primary" onClick={() => setModalOpen(false)}>
                        확인
                    </Button>
                }
                width={500}
            >
                <div style={{ padding: '20px 0' }}>
                    <Alert
                        message="한 줄 요약"
                        description={<Text strong style={{ fontSize: 16 }}>{term.simple}</Text>}
                        type="info"
                        showIcon
                        icon={<BulbOutlined />}
                        style={{ marginBottom: 20 }}
                    />

                    <Card size="small" title="자세한 설명" style={{ marginBottom: 16 }}>
                        <pre style={{
                            whiteSpace: 'pre-wrap',
                            fontFamily: 'inherit',
                            margin: 0,
                            lineHeight: 1.8,
                            color: '#595959'
                        }}>
                            {term.detailed.trim()}
                        </pre>
                    </Card>

                    <Card size="small" title="예시">
                        <Text code>{term.example}</Text>
                    </Card>
                </div>
            </Modal>
        </>
    );
};

// 결과 점수 카드 컴포넌트
export const ScoreCard = ({ metrics }) => {
    const score = calculateScoreCard(metrics);
    if (!score) return null;

    const renderStars = (count, maxCount = 5) => {
        return Array(maxCount).fill(0).map((_, i) => (
            <StarOutlined
                key={i}
                style={{
                    color: i < count ? '#faad14' : '#d9d9d9',
                    fontSize: 16,
                    marginRight: 2
                }}
            />
        ));
    };

    return (
        <Card
            title={
                <Space>
                    <BarChartOutlined />
                    <span>전략 평가 점수표</span>
                    <Tag
                        color={score.gradeColor}
                        style={{ fontSize: 14, padding: '2px 10px', fontWeight: 'bold' }}
                    >
                        {score.grade}등급
                    </Tag>
                </Space>
            }
            style={{ marginTop: 16 }}
        >
            <Alert
                message={score.comment}
                type={score.grade === 'S' || score.grade === 'A' ? 'success' :
                    score.grade === 'B' ? 'info' :
                        score.grade === 'C' ? 'warning' : 'error'}
                showIcon
                style={{ marginBottom: 20 }}
            />

            <Row gutter={[24, 16]}>
                <Col span={12}>
                    <Card size="small" style={{ background: '#f6ffed', border: '1px solid #b7eb8f' }}>
                        <Space direction="vertical" style={{ width: '100%' }}>
                            <Text type="secondary"><SafetyCertificateOutlined /> 안정성</Text>
                            <div>{renderStars(score.stability)}</div>
                            <Text style={{ fontSize: 12, color: '#52c41a' }}>
                                {score.stability >= 4 ? '매우 안정적' :
                                    score.stability >= 3 ? '적절한 수준' : '주의 필요'}
                            </Text>
                        </Space>
                    </Card>
                </Col>

                <Col span={12}>
                    <Card size="small" style={{ background: '#fff7e6', border: '1px solid #ffd591' }}>
                        <Space direction="vertical" style={{ width: '100%' }}>
                            <Text type="secondary"><DollarOutlined /> 수익성</Text>
                            <div>{renderStars(score.profitability)}</div>
                            <Text style={{ fontSize: 12, color: '#faad14' }}>
                                {score.profitability >= 4 ? '높은 수익' :
                                    score.profitability >= 3 ? '양호' : '개선 필요'}
                            </Text>
                        </Space>
                    </Card>
                </Col>

                <Col span={12}>
                    <Card size="small" style={{ background: '#fff1f0', border: '1px solid #ffa39e' }}>
                        <Space direction="vertical" style={{ width: '100%' }}>
                            <Text type="secondary"><WarningOutlined /> 위험도</Text>
                            <div>{renderStars(6 - score.riskLevel)}</div>
                            <Text style={{ fontSize: 12, color: '#f5222d' }}>
                                {score.riskLevel <= 2 ? '낮은 위험' :
                                    score.riskLevel <= 3 ? '적절한 위험' : '높은 위험'}
                            </Text>
                        </Space>
                    </Card>
                </Col>

                <Col span={12}>
                    <Card size="small" style={{ background: '#e6f7ff', border: '1px solid #91d5ff' }}>
                        <Space direction="vertical" style={{ width: '100%' }}>
                            <Text type="secondary"><CheckCircleOutlined /> 신뢰도</Text>
                            <div>{renderStars(score.reliability)}</div>
                            <Text style={{ fontSize: 12, color: '#1890ff' }}>
                                {score.reliability >= 4 ? '높은 신뢰' :
                                    score.reliability >= 3 ? '보통' : '검증 필요'}
                            </Text>
                        </Space>
                    </Card>
                </Col>
            </Row>

            <Divider style={{ margin: '16px 0' }} />

            <div style={{ textAlign: 'center' }}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                    이 점수는 백테스트 결과를 기반으로 한 참고용 지표입니다.
                    실제 투자 결과는 다를 수 있습니다.
                </Text>
            </div>
        </Card>
    );
};

// 추천 설정 프리셋 컴포넌트
export const PresetButtons = ({ onApply }) => {
    const presets = [
        {
            key: 'beginner',
            label: '초보자용 (안전)',
            description: '레버리지 1x, 안전한 설정',
            color: '#52c41a',
            settings: {
                leverage: 1,
                marginMode: 'isolated',
                stopLoss: 3,
                takeProfit: 6,
                includeFundingFee: false
            }
        },
        {
            key: 'moderate',
            label: '중급자용',
            description: '레버리지 3x, 균형잡힌 설정',
            color: '#1890ff',
            settings: {
                leverage: 3,
                marginMode: 'isolated',
                stopLoss: 5,
                takeProfit: 10,
                includeFundingFee: true
            }
        },
        {
            key: 'aggressive',
            label: '공격적 (고위험)',
            description: '레버리지 10x, 고수익 추구',
            color: '#f5222d',
            settings: {
                leverage: 10,
                marginMode: 'isolated',
                stopLoss: 2,
                takeProfit: 5,
                includeFundingFee: true
            }
        }
    ];

    return (
        <Card size="small" style={{ marginBottom: 16, background: '#fafafa' }}>
            <Space direction="vertical" style={{ width: '100%' }}>
                <Text strong>
                    <RocketOutlined style={{ marginRight: 8 }} />
                    원클릭 추천 설정
                </Text>
                <Row gutter={8}>
                    {presets.map(preset => (
                        <Col span={8} key={preset.key}>
                            <Tooltip title={preset.description}>
                                <Button
                                    block
                                    style={{
                                        borderColor: preset.color,
                                        color: preset.color,
                                        height: 'auto',
                                        padding: '8px',
                                        whiteSpace: 'normal'
                                    }}
                                    onClick={() => onApply && onApply(preset.settings)}
                                >
                                    <div style={{ fontSize: 12 }}>{preset.label}</div>
                                </Button>
                            </Tooltip>
                        </Col>
                    ))}
                </Row>
            </Space>
        </Card>
    );
};

// 백테스트 팁 카드
export const BacktestTips = () => {
    const tips = [
        '처음엔 레버리지 1x로 시작하세요',
        '최소 1년 이상의 데이터로 테스트하세요',
        '승률보다 "Profit Factor"가 더 중요해요',
        'MDD 30% 이상이면 위험한 전략이에요',
        '다양한 기간에서 테스트해보세요'
    ];

    return (
        <Card
            size="small"
            title={<><BulbOutlined /> 초보자 꿀팁</>}
            style={{ marginBottom: 16, background: '#fffbe6', border: '1px solid #ffe58f' }}
        >
            {tips.map((tip, i) => (
                <div key={i} style={{ marginBottom: 4, fontSize: 13, display: 'flex', gap: 8 }}>
                    <InfoCircleOutlined style={{ color: '#faad14', fontSize: 12, marginTop: 4 }} />
                    <span>{tip}</span>
                </div>
            ))}
        </Card>
    );
};

export default {
    TermTooltip,
    ScoreCard,
    PresetButtons,
    BacktestTips,
    TERMS_DICTIONARY,
    calculateScoreCard
};
