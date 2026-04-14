import { LoaderCircle } from "lucide-react";

function Spinner({ className = "h-4 w-4" }) {
  return <LoaderCircle className={`${className} animate-spin`} />;
}

export default Spinner;
