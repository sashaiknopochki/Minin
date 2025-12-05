import { Outlet, Link, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  NavigationMenu,
  NavigationMenuList,
  NavigationMenuItem,
  NavigationMenuLink,
  navigationMenuTriggerStyle,
} from "@/components/ui/navigation-menu";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import UserMenu from "@/components/UserMenu";
import { useAuth } from "@/contexts/AuthContext";
import { Menu } from "lucide-react";
import { cn } from "@/lib/utils";
import { useState } from "react";

export default function Layout() {
  const { user } = useAuth();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const isActive = (path: string) => location.pathname === path;

  return (
    <div>
      {/* Header */}
      <header className="w-full py-3">
        <div className="flex items-center justify-between">
          {/* Mobile Menu Button (left side, visible only on mobile) */}
          <div className="md:hidden">
            <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon" className="h-9 w-9 [&_svg]:size-6">
                  <Menu className="h-6 w-6" />
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="w-64 h-full">
                <SheetHeader>
                  <SheetTitle>minin</SheetTitle>
                </SheetHeader>
                <nav className="flex flex-col gap-4 mt-8">
                  <Link
                    to="/translate"
                    onClick={() => setMobileMenuOpen(false)}
                    className={cn(
                      "text-left px-4 py-2 rounded-md transition-colors hover:bg-accent",
                      isActive('/translate') && "font-bold"
                    )}
                  >
                    Translate
                  </Link>
                  <Link
                    to="/learn"
                    onClick={() => setMobileMenuOpen(false)}
                    className={cn(
                      "text-left px-4 py-2 rounded-md transition-colors hover:bg-accent",
                      isActive('/learn') && "font-bold"
                    )}
                  >
                    Learn
                  </Link>
                  <Link
                    to="/practice"
                    onClick={() => setMobileMenuOpen(false)}
                    className={cn(
                      "text-left px-4 py-2 rounded-md transition-colors hover:bg-accent",
                      isActive('/practice') && "font-bold"
                    )}
                  >
                    Practice
                  </Link>
                  <Link
                    to="/history"
                    onClick={() => setMobileMenuOpen(false)}
                    className={cn(
                      "text-left px-4 py-2 rounded-md transition-colors hover:bg-accent",
                      isActive('/history') && "font-bold"
                    )}
                  >
                    History
                  </Link>
                </nav>
              </SheetContent>
            </Sheet>
          </div>

          {/* Logo (centered between menu and auth) */}
          <div className="flex-1 md:flex-none flex justify-center md:justify-start">
            <Link to="/translate">
              <h1 className="text-4xl font-bold text-foreground">minin</h1>
            </Link>
          </div>

          {/* Desktop Navigation (hidden on mobile, visible on desktop) */}
          <div className="hidden md:flex items-baseline gap-4 lg:gap-6 flex-1 justify-center">
            <NavigationMenu>
              <NavigationMenuList className="gap-1">
                <NavigationMenuItem>
                  <NavigationMenuLink
                    asChild
                    className={cn(
                      navigationMenuTriggerStyle(),
                      "cursor-pointer bg-transparent",
                      isActive('/translate') && "font-bold"
                    )}
                  >
                    <Link to="/translate">Translate</Link>
                  </NavigationMenuLink>
                </NavigationMenuItem>
                <NavigationMenuItem>
                  <NavigationMenuLink
                    asChild
                    className={cn(
                      navigationMenuTriggerStyle(),
                      "cursor-pointer bg-transparent",
                      isActive('/learn') && "font-bold"
                    )}
                  >
                    <Link to="/learn">Learn</Link>
                  </NavigationMenuLink>
                </NavigationMenuItem>
                <NavigationMenuItem>
                  <NavigationMenuLink
                    asChild
                    className={cn(
                      navigationMenuTriggerStyle(),
                      "cursor-pointer bg-transparent",
                      isActive('/practice') && "font-bold"
                    )}
                  >
                    <Link to="/practice">Practice</Link>
                  </NavigationMenuLink>
                </NavigationMenuItem>
                <NavigationMenuItem>
                  <NavigationMenuLink
                    asChild
                    className={cn(
                      navigationMenuTriggerStyle(),
                      "cursor-pointer bg-transparent",
                      isActive('/history') && "font-bold"
                    )}
                  >
                    <Link to="/history">History</Link>
                  </NavigationMenuLink>
                </NavigationMenuItem>
              </NavigationMenuList>
            </NavigationMenu>
          </div>

          {/* Authentication - Show either Sign In or User Menu */}
          {user ? (
            <UserMenu />
          ) : (
            <Button
              asChild
              className="h-9 px-4 py-2 shadow-sm"
            >
              <Link to="/login">Sign In</Link>
            </Button>
          )}
        </div>
      </header>

      {/* Page Content */}
      <Outlet />
    </div>
  );
}