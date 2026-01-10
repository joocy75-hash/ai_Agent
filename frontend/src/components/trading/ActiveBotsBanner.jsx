/**
 * ActiveBotsBanner - 실행 중인 봇 상단 배너
 * 활성 봇이 있으면 요약 정보 표시
 */
import React from 'react';
import { Button } from 'antd';
import { RobotOutlined, RightOutlined } from '@ant-design/icons';
import './styles/ActiveBotsBanner.css';

const ActiveBotsBanner = ({
    activeBotCount = 0,
    totalPnl = 0,
    totalPnlPercent = 0,
    onViewAll,
}) => {
    // 활성 봇이 없으면 렌더링하지 않음
    if (activeBotCount === 0) {
        return null;
    }

    const isPositive = totalPnl >= 0;
    const pnlColor = isPositive ? '#00c853' : '#ff5252';
    const pnlSign = isPositive ? '+' : '';

    return (
        <div className="active-bots-banner">
            <div className="banner-content">
                <div className="banner-icon">
                    <RobotOutlined />
                </div>
                <div className="banner-info">
                    <span className="bot-count">
                        <strong>{activeBotCount}</strong>개 봇 실행중
                    </span>
                    <span className="divider">|</span>
                    <span className="pnl-label">총 손익</span>
                    <span
                        className="pnl-value"
                        style={{ color: pnlColor }}
                    >
                        {pnlSign}{totalPnl.toFixed(2)} USDT
                    </span>
                    <span
                        className="pnl-percent"
                        style={{ color: pnlColor }}
                    >
                        ({pnlSign}{totalPnlPercent.toFixed(2)}%)
                    </span>
                </div>
            </div>
            {onViewAll && (
                <Button
                    type="text"
                    className="view-all-button"
                    onClick={onViewAll}
                >
                    내 봇 보기 <RightOutlined />
                </Button>
            )}
        </div>
    );
};

export default ActiveBotsBanner;
