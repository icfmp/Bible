// Bible contributors, GPL-2.0-only. Reference bounds only; no source text.
// Included once, outside the SWORD namespace, by versificationmgr.cpp.
#include <fstream>
#include <sstream>
#include <set>
#include <mutex>

extern "C" SWDLLEXPORT int bible_register_source_index(const char *path) {
    static std::mutex guard;
    std::lock_guard<std::mutex> locked(guard);
    try {
        if (!path) return 1;
        std::ifstream input(path, std::ios::binary | std::ios::ate);
        if (!input || input.tellg() < 1 || input.tellg() > 262144) return 1;
        input.seekg(0);
        std::string signature, name, line;
        if (!std::getline(input, line)) return 1;
        std::istringstream header(line);
        if (!(header >> signature >> name) || signature != "BIBLE-VRS-1" ||
                name.substr(0, 10) != "YouVersion" || name.size() < 11 || name.size() > 19 || name[10] == '0') return 1;
        std::string extra;
        if (header >> extra) return 1;
        for (size_t i = 10; i < name.size(); ++i) if (name[i] < '0' || name[i] > '9') return 1;
        struct SourceBook { std::string code; int testament; std::vector<int> verses; };
        std::vector<SourceBook> books;
        std::set<std::string> seen;
        size_t chapters = 0, slots = 0;
        int previousTestament = 1, otCount = 0;
        while (std::getline(input, line)) {
            if (line.empty() || line.size() > 16384 || books.size() >= 100) return 1;
            std::istringstream row(line);
            SourceBook book; int count;
            if (!(row >> book.testament >> book.code >> count) ||
                    book.testament < previousTestament || book.testament > 2 || count < 1 || count > 255 ||
                    book.code.size() < 2 || book.code.size() > 16 || !seen.insert(book.code).second) return 1;
            for (char c : book.code) if (!((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9'))) return 1;
            previousTestament = book.testament;
            if (book.testament == 1) ++otCount;
            for (int i = 0; i < count; ++i) {
                int maximum;
                if (!(row >> maximum) || maximum < 0 || maximum > 2000) return 1;
                book.verses.push_back(maximum); slots += maximum;
            }
            if (row >> extra) return 1;
            chapters += count;
            if (chapters > 10000 || slots > 500000) return 1;
            books.push_back(book);
        }
        if (books.empty() || !slots || !input.eof()) return 1;
        auto manager = sword::VersificationMgr::getSystemVersificationMgr();
        if (const auto existing = manager->getVersificationSystem(name.c_str())) {
            // Never replace an index while live keys/modules/notes refer to it.
            if (existing->getBookCount() != (int)books.size() || existing->getBMAX()[0] != otCount) return 1;
            for (size_t i = 0; i < books.size(); ++i) {
                const auto native = existing->getBook(i);
                if (books[i].code != native->getOSISName() || (int)books[i].verses.size() != native->getChapterMax()) return 1;
                for (size_t j = 0; j < books[i].verses.size(); ++j)
                    if (books[i].verses[j] != native->getVerseMax(j + 1)) return 1;
            }
            return 0;
        }
        std::vector<sword::sbook> ot, nt;
        std::vector<int> maxima;
        const auto names = manager->getVersificationSystem("KJVA");
        for (const auto &book : books) {
            // Reuse only display names for exactly matching OSIS identifiers;
            // verse bounds and alignment remain entirely source-specific.
            const char *longName = book.code.c_str();
            if (names) for (int i = 0; i < names->getBookCount(); ++i) {
                const auto candidate = names->getBook(i);
                if (book.code == candidate->getOSISName()) { longName = candidate->getLongName(); break; }
            }
            sword::sbook record = {longName, book.code.c_str(), book.code.c_str(), (unsigned char)book.verses.size(), nullptr};
            (book.testament == 1 ? ot : nt).push_back(record);
            maxima.insert(maxima.end(), book.verses.begin(), book.verses.end());
        }
        sword::sbook end = {nullptr, nullptr, nullptr, 0, nullptr};
        ot.push_back(end); nt.push_back(end);
        // SWORD copies book strings and verse bounds into its own System.
        manager->registerVersificationSystem(name.c_str(), ot.data(), nt.data(), maxima.data());
        return 0;
    } catch (...) { return 1; }
}
