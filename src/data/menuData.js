export const menuItems = [
  {
    id: 1,
    label: '首页',
    path: '/',
  },
  {
    id: 2,
    label: '产品',
    path: '/products',
    children: [
      { id: 21, label: '产品列表', path: '/products/list' },
      { id: 22, label: '产品详情', path: '/products/detail' },
      {
        id: 23,
        label: '高级功能',
        children: [
          { id: 231, label: '功能A', path: '/products/advanced/a' },
          { id: 232, label: '功能B', path: '/products/advanced/b' },
        ],
      },
    ],
  },
  {
    id: 3,
    label: '服务',
    path: '/services',
    children: [
      { id: 31, label: '咨询服务', path: '/services/consulting' },
      { id: 32, label: '技术支持', path: '/services/support' },
    ],
  },
  {
    id: 4,
    label: '关于我们',
    path: '/about',
  },
]

export default menuItems
