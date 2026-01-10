import { useState, useEffect } from 'react';
import { Layout, Menu, Avatar, Dropdown, Space, Drawer, Button } from 'antd';
import { useNavigate, useLocation } from 'react-router-dom';
import {
    DashboardOutlined,
    LineChartOutlined,
    SettingOutlined,
    LogoutOutlined,
    BellOutlined,
    UserOutlined,
    MenuFoldOutlined,
    MenuUnfoldOutlined,
    FundOutlined,
    MenuOutlined,
    CloseOutlined,
    RobotOutlined,
    RocketOutlined,
} from '@ant-design/icons';
import { useAuth } from '../../context/AuthContext';
import NotificationBell from '../NotificationBell';

const { Header, Sider, Content } = Layout;

// 모바일 브레이크포인트
const MOBILE_BREAKPOINT = 768;

export default function MainLayout({ children }) {
    const [collapsed, setCollapsed] = useState(false);
    const [isMobile, setIsMobile] = useState(false);
    const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);
    const navigate = useNavigate();
    const location = useLocation();
    const { user, logout } = useAuth();

    // 화면 크기 감지
    useEffect(() => {
        const checkMobile = () => {
            const mobile = window.innerWidth < MOBILE_BREAKPOINT;
            setIsMobile(mobile);
            if (mobile) {
                setCollapsed(true);
            }
        };

        checkMobile();
        window.addEventListener('resize', checkMobile);
        return () => window.removeEventListener('resize', checkMobile);
    }, []);

    // 페이지 변경 시 모바일 드로어 닫기
    useEffect(() => {
        setMobileDrawerOpen(false);
    }, [location.pathname]);

    const menuItems = [
        {
            key: '/dashboard',
            icon: <DashboardOutlined />,
            label: '대시보드',
        },
        {
            key: '/trading',
            icon: <LineChartOutlined />,
            label: '트레이딩',
        },
        // 전략 관리 페이지 숨김 (재설계 후 활성화 예정)
        // {
        //     key: '/strategy',
        //     icon: <RocketOutlined />,
        //     label: '전략 관리',
        // },
        // 봇 관리 페이지 숨김 (멀티봇 시스템 재설계 후 활성화 예정)
        // {
        //     key: '/bots',
        //     icon: <RobotOutlined />,
        //     label: '봇 관리',
        // },
        {
            key: '/history',
            icon: <FundOutlined />,
            label: '거래 내역',
        },
        {
            key: '/alerts',
            icon: <BellOutlined />,
            label: '알림',
        },
        {
            key: '/settings',
            icon: <SettingOutlined />,
            label: '설정',
        },
    ];

    const handleMenuClick = ({ key }) => {
        if (key === 'logout') {
            logout();
            navigate('/login');
        } else {
            navigate(key);
            if (isMobile) {
                setMobileDrawerOpen(false);
            }
        }
    };

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    const userMenuItems = [
        {
            key: 'profile',
            icon: <UserOutlined />,
            label: '프로필',
            onClick: () => navigate('/settings'),
        },
        {
            key: 'settings',
            icon: <SettingOutlined />,
            label: '설정',
            onClick: () => navigate('/settings'),
        },
        {
            type: 'divider',
        },
        {
            key: 'logout',
            icon: <LogoutOutlined />,
            label: '로그아웃',
            onClick: handleLogout,
            danger: true,
        },
    ];

    // 사이드바 컨텐츠 (데스크톱 & 모바일 공용)
    const SidebarContent = () => (
        <>
            {/* Logo */}
            <div
                style={{
                    height: 72,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
                    padding: isMobile ? '0 20px' : 0,
                    background: 'rgba(255, 255, 255, 0.02)',
                }}
            >
                <div
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 10,
                        width: '100%',
                        justifyContent: isMobile ? 'space-between' : 'center',
                    }}
                >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        {/* 로고 아이콘 */}
                        <div
                            style={{
                                width: 38,
                                height: 38,
                                background: '#ffffff',
                                borderRadius: 10,
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
                            }}
                        >
                            <span style={{ fontSize: 20, lineHeight: 1 }}>⚡</span>
                        </div>
                        {/* 로고 텍스트 */}
                        {(!collapsed || isMobile) && (
                            <span
                                style={{
                                    color: '#ffffff',
                                    fontSize: 18,
                                    fontWeight: 700,
                                    letterSpacing: '-0.3px',
                                }}
                            >
                                Deep Signal
                            </span>
                        )}
                    </div>
                    {isMobile && (
                        <CloseOutlined
                            onClick={() => setMobileDrawerOpen(false)}
                            style={{
                                color: 'white',
                                fontSize: 18,
                                cursor: 'pointer',
                                padding: 8,
                            }}
                        />
                    )}
                </div>
            </div>

            {/* Menu */}
            <Menu
                theme="dark"
                mode="inline"
                selectedKeys={[location.pathname]}
                items={menuItems}
                onClick={handleMenuClick}
                style={{
                    background: 'transparent',
                    borderRight: 'none',
                    marginTop: 16,
                    padding: '0 12px',
                }}
            />

            {/* 모바일에서 하단 유저 정보 표시 */}
            {isMobile && (
                <div
                    style={{
                        position: 'absolute',
                        bottom: 0,
                        left: 0,
                        right: 0,
                        padding: 16,
                        borderTop: '1px solid rgba(255, 255, 255, 0.1)',
                    }}
                >
                    <div
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 12,
                            marginBottom: 12,
                        }}
                    >
                        <Avatar
                            size={40}
                            style={{
                                background: 'linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%)',
                            }}
                        >
                            {user?.email?.[0]?.toUpperCase() || 'U'}
                        </Avatar>
                        <div>
                            <div style={{ color: 'white', fontWeight: 500 }}>
                                {user?.email?.split('@')[0] || 'User'}
                            </div>
                            <div style={{ color: 'rgba(255,255,255,0.6)', fontSize: 12 }}>
                                {user?.email || ''}
                            </div>
                        </div>
                    </div>
                    <Button
                        danger
                        block
                        icon={<LogoutOutlined />}
                        onClick={handleLogout}
                        style={{
                            background: 'rgba(239, 68, 68, 0.2)',
                            borderColor: 'rgba(239, 68, 68, 0.5)',
                            color: '#fca5a5',
                        }}
                    >
                        로그아웃
                    </Button>
                </div>
            )}
        </>
    );

    return (
        <Layout style={{ minHeight: '100vh' }}>
            {/* 모바일 드로어 */}
            {isMobile && (
                <Drawer
                    placement="left"
                    open={mobileDrawerOpen}
                    onClose={() => setMobileDrawerOpen(false)}
                    closable={false}
                    width={280}
                    bodyStyle={{
                        padding: 0,
                        background: '#000000',
                    }}
                    headerStyle={{ display: 'none' }}
                >
                    <SidebarContent />
                </Drawer>
            )}

            {/* 데스크톱 사이드바 */}
            {!isMobile && (
                <Sider
                    collapsible
                    collapsed={collapsed}
                    onCollapse={setCollapsed}
                    trigger={null}
                    width={260}
                    style={{
                        overflow: 'auto',
                        height: '100vh',
                        position: 'fixed',
                        left: 0,
                        top: 0,
                        bottom: 0,
                        background: '#000000',
                        boxShadow: '2px 0 8px rgba(0, 0, 0, 0.3)',
                    }}
                >
                    <SidebarContent />
                </Sider>
            )}

            {/* Main Content Area */}
            {/* 성능 최적화: 전환 애니메이션 완전 제거 - 즉각 반응 */}
            <Layout
                style={{
                    marginLeft: isMobile ? 0 : (collapsed ? 80 : 260),
                    background: '#f5f5f7',
                    minHeight: '100vh',
                }}
            >
                {/* Header */}
                <Header
                    style={{
                        padding: isMobile ? '0 16px' : '0 32px',
                        background: '#ffffff',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.04)',
                        borderBottom: '1px solid #f5f5f7',
                        position: 'sticky',
                        top: 0,
                        zIndex: 100,
                        height: 64,
                    }}
                >
                    {/* Left - Menu Toggle & Title */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: isMobile ? 8 : 16 }}>
                        <div
                            onClick={() => isMobile ? setMobileDrawerOpen(true) : setCollapsed(!collapsed)}
                            style={{
                                cursor: 'pointer',
                                fontSize: 18,
                                color: '#6b7280',
                                padding: '8px 10px',
                                borderRadius: 8,
                                transition: 'all 0.2s',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                            }}
                        >
                            {isMobile ? (
                                <MenuOutlined />
                            ) : (
                                collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />
                            )}
                        </div>
                        <div>
                            <h1 style={{
                                margin: 0,
                                fontSize: isMobile ? 16 : 20,
                                fontWeight: 600,
                                color: '#1d1d1f',
                                whiteSpace: 'nowrap',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                maxWidth: isMobile ? 150 : 'none',
                            }}>
                                {menuItems.find(item => item.key === location.pathname)?.label || 'Dashboard'}
                            </h1>
                        </div>
                    </div>

                    {/* Right - Notifications & User */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: isMobile ? 8 : 16 }}>
                        <NotificationBell />

                        {/* 데스크톱에서만 유저 드롭다운 표시 */}
                        {!isMobile && (
                            <Dropdown
                                menu={{ items: userMenuItems }}
                                placement="bottomRight"
                                trigger={['click']}
                            >
                                <Space
                                    style={{
                                        cursor: 'pointer',
                                        padding: '8px 14px',
                                        borderRadius: 10,
                                        transition: 'all 0.2s',
                                    }}
                                    onMouseEnter={(e) => {
                                        e.currentTarget.style.background = '#f3f4f6';
                                    }}
                                    onMouseLeave={(e) => {
                                        e.currentTarget.style.background = 'transparent';
                                    }}
                                >
                                    <Avatar
                                        size={34}
                                        style={{
                                            background: '#1d1d1f',
                                            fontSize: 14,
                                            fontWeight: 600,
                                        }}
                                    >
                                        {user?.email?.[0]?.toUpperCase() || 'U'}
                                    </Avatar>
                                    <span style={{
                                        color: '#374151',
                                        fontSize: 14,
                                        fontWeight: 500,
                                    }}>
                                        {user?.email?.split('@')[0] || 'User'}
                                    </span>
                                </Space>
                            </Dropdown>
                        )}

                        {/* 모바일에서는 아바타만 표시 */}
                        {isMobile && (
                            <Avatar
                                size={34}
                                style={{
                                    background: '#1d1d1f',
                                    fontSize: 14,
                                    cursor: 'pointer',
                                    fontWeight: 600,
                                }}
                                onClick={() => setMobileDrawerOpen(true)}
                            >
                                {user?.email?.[0]?.toUpperCase() || 'U'}
                            </Avatar>
                        )}
                    </div>
                </Header>

                {/* Content */}
                <Content
                    style={{
                        padding: isMobile ? 0 : 28,
                        minHeight: 'calc(100vh - 64px)',
                        background: 'transparent',
                    }}
                >
                    {children}
                </Content>
            </Layout>
        </Layout>
    );
}
