import React, {
  ReactNode,
  createContext,
  PropsWithChildren,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useDrag } from "react-dnd";

interface DrawerConfig {
  title?: string;
  content: ReactNode;
  actions?: Array<{ title: string; onClick(): void }>;
}

interface DrawerContextType {
  config: DrawerConfig;
  open: boolean;
  coordinates: [number, number];
  reveal(config: DrawerConfig): void;
  hide(): void;
  show(): void;
  toggle(): void;
  updateCoordinates(to: [number, number]): void;
}

const DRAWER_COORDINATES_STORAGE_KEY = "Drawer/Coordinates";

const DEFAULT_DRAWER_CONFIG = {
  title: "",
  content: null,
  actions: [],
};

const DrawerContext = createContext<DrawerContextType>({
  config: DEFAULT_DRAWER_CONFIG,
  open: false,
  coordinates: [0, 0] as [number, number],
  reveal() {},
  hide() {},
  show() {},
  toggle() {},
  updateCoordinates() {},
});

export function useDrawer() {
  const values = useContext(DrawerContext);
  return values;
}

export function DrawerProvider({ children }: PropsWithChildren) {
  const [open, setOpen] = useState(false);
  const [config, setConfig] = useState<DrawerConfig>(DEFAULT_DRAWER_CONFIG);
  const [coordinates, setCoordinates] = useState([0, 0] as [number, number]);
  const reveal = useCallback((config: DrawerConfig) => {
    setConfig(config);
    show();
  }, []);
  const hide = useCallback(() => {
    setOpen(false);
  }, []);
  const show = useCallback(() => {
    setOpen(true);
  }, []);
  const toggle = useCallback(() => {
    setOpen((prev) => !prev);
  }, []);
  const context = useMemo(
    () => ({
      config,
      open,
      coordinates,
      reveal,
      hide,
      show,
      toggle,
      updateCoordinates: setCoordinates,
    }),
    [config, open, coordinates, reveal, hide, show, toggle]
  );

  // Load coordinates.
  useEffect(() => {
    const persisted = window.localStorage.getItem(
      DRAWER_COORDINATES_STORAGE_KEY
    );

    if (persisted) {
      setCoordinates(JSON.parse(persisted));
    }
  }, []);

  // Persist coordinates.
  useEffect(() => {
    window.localStorage.setItem(
      DRAWER_COORDINATES_STORAGE_KEY,
      JSON.stringify(coordinates)
    );
  }, [coordinates]);

  return (
    <DrawerContext.Provider value={context}>{children}</DrawerContext.Provider>
  );
}

export function Drawer() {
  const {
    config: { title = "", content, actions = [] },
    open,
    coordinates,
    updateCoordinates,
    hide,
  } = useDrawer();
  const [x, y] = coordinates;
  const [{ isDragging }, dragRef] = useDrag({
    type: "drawer",
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
  });
  const lastMousePosition = useRef([0, 0]);

  useEffect(() => {
    const handleMouseMove = (event: MouseEvent) =>
      (lastMousePosition.current = [event.clientX, event.clientY]);

    window.addEventListener("mousemove", handleMouseMove);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
    };
  }, []);

  useEffect(() => {
    if (open) {
      const chatWrapper = document.getElementById("chatWrapper");
      const chatWrapperBox = chatWrapper.getBoundingClientRect();

      updateCoordinates([chatWrapperBox.left, chatWrapperBox.top]);
    }
  }, [open]);

  useEffect(() => {
    if (isDragging) {
      const onRelease = (event: DragEvent) => {
        const drawer = document.getElementById("drawer");
        const drawerBox = drawer.getBoundingClientRect();
        const [mouseX, mouseY] = lastMousePosition.current;
        const xDiff = mouseX - drawerBox.left;
        const yDiff = mouseY - drawerBox.top;

        updateCoordinates([event.clientX - xDiff, event.clientY - yDiff]);
      };

      document.addEventListener("drop", onRelease);

      return () => {
        document.removeEventListener("drop", onRelease);
      };
    }
  }, [isDragging]);

  return (
    <div
      id="drawer"
      className="App-drawer"
      ref={dragRef}
      style={{
        top: y,
        left: x,
      }}
    >
      <button
        type="button"
        className="App-drawer--close btn btn-default"
        onClick={hide}
      >
        X
      </button>
      <div className="App-drawer--content">{content}</div>
      {actions.map((action) => (
        <button
          key={action.title}
          type="button"
          onClick={action.onClick}
          className="btn btn-secondary"
        >
          {action.title}
        </button>
      ))}
    </div>
  );
}
