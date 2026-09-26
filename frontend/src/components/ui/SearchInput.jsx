import { forwardRef } from "react";
import { Input } from "./Input";
import { SearchIcon } from "./Icons";

/**
 * The search field used everywhere a query is typed (navbar, seller/staff
 * lists, filters). It is just an Input with the two affordances every search
 * bar in this app must have: the search glyph on the left and a clear (X)
 * button on the right that appears only while there is text to clear.
 */
export const SearchInput = forwardRef(function SearchInput(
  { leadingIcon = SearchIcon, clearable = true, clearLabel = "Clear search", ...props },
  ref
) {
  return (
    <Input
      ref={ref}
      leadingIcon={leadingIcon}
      clearable={clearable}
      clearLabel={clearLabel}
      type="search"
      {...props}
    />
  );
});
