import { useAuth } from "@/contexts/AuthContext";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
  DrawerDescription,
} from "@/components/ui/drawer";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { LogOut, User as UserIcon } from "lucide-react";
import { useMediaQuery } from "@/hooks/use-media-query";

export default function UserMenu() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const isMobile = useMediaQuery("(max-width: 767px)");
  const navigate = useNavigate();

  if (!user) return null;

  // Get user initials for avatar fallback
  const getInitials = (name: string) => {
    const parts = name.split(" ");
    if (parts.length >= 2) {
      return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
  };

  const handleLogout = async () => {
    await logout();
    setOpen(false);
  };

  const handleProfileClick = () => {
    navigate("/profile");
    setOpen(false);
  };

  const userAvatar = (
    <Avatar className="h-9 w-9 cursor-pointer">
      <AvatarImage src={user.picture} alt={user.name} />
      <AvatarFallback className="bg-primary text-primary-foreground">
        {getInitials(user.name)}
      </AvatarFallback>
    </Avatar>
  );

  // Mobile: Use Drawer
  if (isMobile) {
    return (
      <Drawer open={open} onOpenChange={setOpen}>
        <button
          onClick={() => setOpen(true)}
          className="flex items-center gap-2 focus:outline-none"
        >
          {userAvatar}
        </button>
        <DrawerContent>
          <DrawerHeader className="text-left">
            <DrawerTitle>{user.name}</DrawerTitle>
            <DrawerDescription className="text-muted-foreground">
              {user.email}
            </DrawerDescription>
          </DrawerHeader>
          <div className="px-4 pb-6">
            <DrawerClose asChild>
              <button
                onClick={handleProfileClick}
                className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-accent"
              >
                <UserIcon className="h-4 w-4" />
                <span>Profile</span>
              </button>
            </DrawerClose>
            <DrawerClose asChild>
              <button
                onClick={handleLogout}
                className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-accent mt-2"
              >
                <LogOut className="h-4 w-4" />
                <span>Log out</span>
              </button>
            </DrawerClose>
          </div>
        </DrawerContent>
      </Drawer>
    );
  }

  // Desktop/Tablet: Use DropdownMenu
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button className="flex items-center gap-2 focus:outline-none">
          {userAvatar}
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>
          <div className="flex flex-col space-y-1">
            <p className="text-sm font-medium leading-none">{user.name}</p>
            <p className="text-xs leading-none text-muted-foreground">
              {user.email}
            </p>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={handleProfileClick} className="cursor-pointer">
          <UserIcon className="mr-2 h-4 w-4" />
          <span>Profile</span>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={handleLogout} className="cursor-pointer">
          <LogOut className="mr-2 h-4 w-4" />
          <span>Log out</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}