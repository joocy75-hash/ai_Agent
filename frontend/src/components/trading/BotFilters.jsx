/**
 * BotFilters - 정렬/필터 컨트롤
 * Bitget 스타일 다크 테마 드롭다운
 *
 * @param {string} sortBy - 정렬 기준 ('roi' | 'users' | 'new')
 * @param {Function} onSortChange - 정렬 변경 콜백
 * @param {string|null} filterSymbol - 필터링할 심볼
 * @param {Function} onFilterChange - 필터 변경 콜백
 * @param {Array} symbols - 사용 가능한 심볼 목록
 * @param {Function} onRefresh - 새로고침 콜백
 * @param {boolean} loading - 로딩 상태
 */

import { Select, Button, Space } from 'antd';
import { ReloadOutlined, SortAscendingOutlined, FilterOutlined } from '@ant-design/icons';

const { Option } = Select;

// 정렬 옵션
const SORT_OPTIONS = [
    { value: 'roi', label: 'Highest ROI' },
    { value: 'users', label: 'Most Users' },
    { value: 'new', label: 'Newest' },
];

// 다크 테마 Select 스타일
const darkSelectStyle = {
    minWidth: 140,
};

// Select 드롭다운 다크 테마 CSS
const darkThemeStyles = `
    .bot-filter-select .ant-select-selector {
        background: transparent !important;
        border: 1px solid #3d3d3d !important;
        border-radius: 8px !important;
        color: #ffffff !important;
        height: 36px !important;
    }

    .bot-filter-select .ant-select-selector:hover {
        border-color: #5856d6 !important;
    }

    .bot-filter-select.ant-select-focused .ant-select-selector {
        border-color: #5856d6 !important;
        box-shadow: 0 0 0 2px rgba(88, 86, 214, 0.2) !important;
    }

    .bot-filter-select .ant-select-selection-item {
        color: #ffffff !important;
        line-height: 34px !important;
    }

    .bot-filter-select .ant-select-arrow {
        color: #86868b !important;
    }

    .bot-filter-select .ant-select-selection-placeholder {
        color: #86868b !important;
    }

    /* 드롭다운 팝업 스타일 */
    .bot-filter-dropdown {
        background: #252525 !important;
        border: 1px solid #3d3d3d !important;
        border-radius: 10px !important;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4) !important;
        padding: 4px !important;
    }

    .bot-filter-dropdown .ant-select-item {
        color: #ffffff !important;
        border-radius: 6px !important;
        padding: 8px 12px !important;
    }

    .bot-filter-dropdown .ant-select-item:hover {
        background: #3d3d3d !important;
    }

    .bot-filter-dropdown .ant-select-item-option-selected {
        background: rgba(88, 86, 214, 0.2) !important;
        font-weight: 600 !important;
    }

    .bot-filter-dropdown .ant-select-item-option-active {
        background: #3d3d3d !important;
    }

    /* 새로고침 버튼 */
    .bot-refresh-btn {
        background: transparent !important;
        border: 1px solid #3d3d3d !important;
        border-radius: 8px !important;
        color: #86868b !important;
        width: 36px !important;
        height: 36px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    .bot-refresh-btn:hover {
        border-color: #5856d6 !important;
        color: #5856d6 !important;
    }

    .bot-refresh-btn:disabled {
        opacity: 0.5 !important;
    }

    .bot-refresh-btn .anticon {
        animation: none;
    }

    .bot-refresh-btn.loading .anticon {
        animation: spin 1s linear infinite;
    }

    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
`;

export default function BotFilters({
    sortBy = 'roi',
    onSortChange,
    filterSymbol = null,
    onFilterChange,
    symbols = [],
    onRefresh,
    loading = false
}) {
    return (
        <>
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: 12,
            }}>
                {/* 왼쪽: 정렬 & 필터 */}
                <Space size={12} wrap>
                    {/* 정렬 드롭다운 */}
                    <Select
                        value={sortBy}
                        onChange={onSortChange}
                        style={darkSelectStyle}
                        className="bot-filter-select"
                        popupClassName="bot-filter-dropdown"
                        suffixIcon={<SortAscendingOutlined />}
                    >
                        {SORT_OPTIONS.map((opt) => (
                            <Option key={opt.value} value={opt.value}>
                                {opt.label}
                            </Option>
                        ))}
                    </Select>

                    {/* 심볼 필터 드롭다운 */}
                    <Select
                        value={filterSymbol}
                        onChange={onFilterChange}
                        style={{ ...darkSelectStyle, minWidth: 160 }}
                        className="bot-filter-select"
                        popupClassName="bot-filter-dropdown"
                        placeholder="All Symbols"
                        allowClear
                        suffixIcon={<FilterOutlined />}
                    >
                        {symbols.map((symbol) => (
                            <Option key={symbol} value={symbol}>
                                {symbol}
                            </Option>
                        ))}
                    </Select>
                </Space>

                {/* 오른쪽: 새로고침 버튼 */}
                <Button
                    icon={<ReloadOutlined />}
                    onClick={onRefresh}
                    disabled={loading}
                    className={`bot-refresh-btn ${loading ? 'loading' : ''}`}
                />
            </div>
            <style>{darkThemeStyles}</style>
        </>
    );
}
