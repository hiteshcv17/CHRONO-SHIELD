import React, { createContext, useContext, useState, useEffect } from "react";

type Theme = "dark" | "light" | "solarized";

interface ThemeContextType {
  theme: Theme;
  setTheme: (t: Theme) => void;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = localStorage.getItem("chronoshield-theme");
    return (saved as Theme) || "dark";
  });

  const toggleTheme = () => {
    setTheme((prev) => {
      if (prev === "dark") return "light";
      if (prev === "light") return "solarized";
      return "dark";
    });
  };

  useEffect(() => {
    localStorage.setItem("chronoshield-theme", theme);
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
};
