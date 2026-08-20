import { ReactNode } from "react";

const Layout = ({ children }: { children: ReactNode }) => {
  return <div className="min-h-screen bg-[#0b0b14] text-white">{children}</div>;
};

export default Layout;