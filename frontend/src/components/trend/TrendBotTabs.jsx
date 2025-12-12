/**
 * TrendBotTabs - AI 추세 봇 템플릿
 *
 * AI 탭: 관리자가 만든 AI 추세 봇 템플릿 목록
 */
import React from 'react';
import { ThunderboltOutlined } from '@ant-design/icons';
import { TrendTemplateList } from './templates';
import './TrendBotTabs.css';

const TrendBotTabs = ({
    availableBalance = 0,     // 가용 잔액
    onBotCreated,            // 봇 생성 완료 콜백
}) => {
    return (
        <div className="trend-bot-tabs">
            <div className="ai-trend-header">
                <ThunderboltOutlined style={{ marginRight: 8 }} />
                <span>AI 추천 추세 전략</span>
            </div>
            <TrendTemplateList
                availableBalance={availableBalance}
                onBotCreated={onBotCreated}
            />
        </div>
    );
};

export default TrendBotTabs;
