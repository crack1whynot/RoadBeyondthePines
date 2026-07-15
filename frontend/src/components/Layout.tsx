type LayoutProps = {
  children: React.ReactNode;
};

const Layout = ({ children }: LayoutProps) => {
  return <div className="min-h-screen bg-slate-950">{children}</div>;
};

export default Layout;
