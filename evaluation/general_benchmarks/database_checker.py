from typing import List, Dict, Optional

from sqlalchemy import func

from app.databases.postgres_new.entities import Library, StringToLibrary
from app.databases.postgres_new.postgres import session_generator


def get_library_string_counts(library_names: List[str]) -> Dict[str, Optional[int]]:
    """
    根据库名列表查询每个库的字符串数量

    Args:
        library_names: 库名列表

    Returns:
        Dict[library_name, string_count] - 库名到字符串数量的映射，如果库不存在则为None
    """
    with session_generator() as session:
        result = {}

        # 查询所有指定库名的字符串数量
        query = session.query(
            Library.name,
            func.count(StringToLibrary.string_id).label('string_count')
        ).select_from(
            Library
        ).outerjoin(
            StringToLibrary, Library.id == StringToLibrary.library_id
        ).filter(
            Library.name.in_(library_names)
        ).group_by(
            Library.id, Library.name
        )

        # 执行查询并构建已找到库的结果
        found_libraries = {}
        for library_name, string_count in query.all():
            found_libraries[library_name] = string_count

        # 为所有输入的库名设置结果
        for library_name in library_names:
            if library_name in found_libraries:
                result[library_name] = found_libraries[library_name]
            else:
                result[library_name] = None

        return result


def analyze_all_libraries_string_counts():
    """
    分析所有库的字符串数量并分组打印统计结果
    """
    with session_generator() as session:
        # 查询所有库及其字符串数量
        query = session.query(
            Library.name,
            func.count(StringToLibrary.string_id).label('string_count')
        ).select_from(
            Library
        ).outerjoin(
            StringToLibrary, Library.id == StringToLibrary.library_id
        ).group_by(
            Library.id, Library.name
        ).order_by(
            func.count(StringToLibrary.string_id).desc()
        )

        results = query.all()

        # 分类统计
        no_strings = []  # 收录了但没有字符串的库
        libraries_with_strings = []  # 有字符串的库

        for library_name, string_count in results:
            if string_count == 0:
                no_strings.append(library_name)
            else:
                libraries_with_strings.append((library_name, string_count))

        # 定义区间
        intervals = [
            (1, 10, "1-10"),
            (11, 30, "11-30"),
            (31, 50, "31-50"),
            (51, 100, "51-100"),
            (101, 500, "101-500"),
            (501, 1000, "501-1000"),
            (1001, 5000, "1001-5000"),
            (5001, float('inf'), "5000+")
        ]

        # 按区间分组
        interval_stats = {interval[2]: [] for interval in intervals}

        for library_name, string_count in libraries_with_strings:
            for min_val, max_val, interval_name in intervals:
                if min_val <= string_count <= max_val:
                    interval_stats[interval_name].append((library_name, string_count))
                    break

        # 打印统计结果
        total_libraries = len(results)

        print("=" * 80)
        print(f"📊 库字符串数量统计分析")
        print("=" * 80)

        print(f"\n📈 总体统计:")
        print(f"   总库数量: {total_libraries}")
        print(f"   有字符串的库: {len(libraries_with_strings)}")
        print(f"   没有字符串的库: {len(no_strings)}")

        # 1. 没有字符串的库
        print(f"\n🔍 收录了但没有字符串的库 ({len(no_strings)}个):")
        if no_strings:
            # 分行显示，每行最多5个
            for i in range(0, len(no_strings), 5):
                batch = no_strings[i:i + 5]
                print(f"   {', '.join(batch)}")
        else:
            print("   无")

        # 2. 按区间统计有字符串的库
        print(f"\n📊 字符串数量区间分布:")
        for min_val, max_val, interval_name in intervals:
            libraries_in_interval = interval_stats[interval_name]
            count = len(libraries_in_interval)
            if count > 0:
                percentage = (count / len(libraries_with_strings)) * 100 if libraries_with_strings else 0
                print(f"\n   📂 {interval_name} 个字符串 ({count}个库, {percentage:.1f}%):")

                # 排序并显示前几个库作为示例
                libraries_in_interval.sort(key=lambda x: x[1], reverse=True)

                if count <= 10:
                    # 如果库数量少，全部显示
                    for lib_name, str_count in libraries_in_interval:
                        print(f"      • {lib_name}: {str_count}")
                else:
                    # 如果库数量多，显示前5个和统计信息
                    for lib_name, str_count in libraries_in_interval[:5]:
                        print(f"      • {lib_name}: {str_count}")
                    print(f"      ... 还有 {count - 5} 个库")

        # 3. Top 10 字符串最多的库
        if libraries_with_strings:
            print(f"\n🏆 字符串数量 Top 10:")
            top_10 = sorted(libraries_with_strings, key=lambda x: x[1], reverse=True)[:10]
            for i, (lib_name, str_count) in enumerate(top_10, 1):
                print(f"   {i:2d}. {lib_name}: {str_count:,}")

        print("\n" + "=" * 80)


def get_library_string_count_summary():
    """
    获取库字符串数量的简要统计信息（返回数据而不是打印）

    Returns:
        dict: 包含统计信息的字典
    """
    with session_generator() as session:
        # 查询所有库及其字符串数量
        query = session.query(
            Library.name,
            func.count(StringToLibrary.string_id).label('string_count')
        ).select_from(
            Library
        ).outerjoin(
            StringToLibrary, Library.id == StringToLibrary.library_id
        ).group_by(
            Library.id, Library.name
        )

        results = query.all()

        # 统计信息
        total_libraries = len(results)
        no_strings_count = sum(1 for _, count in results if count == 0)
        with_strings_count = total_libraries - no_strings_count

        # 字符串数量统计
        string_counts = [count for _, count in results if count > 0]

        summary = {
            'total_libraries': total_libraries,
            'libraries_with_strings': with_strings_count,
            'libraries_without_strings': no_strings_count,
            'max_strings': max(string_counts) if string_counts else 0,
            'min_strings': min(string_counts) if string_counts else 0,
            'avg_strings': sum(string_counts) / len(string_counts) if string_counts else 0
        }

        return summary

if __name__ == '__main__':
    # Example usage
    library_names = ["openssl", "libpng"]
    counts = get_library_string_counts(library_names)
    for name, count in counts.items():
        print(f"{name}: {count}")



    # 打印详细分析
    analyze_all_libraries_string_counts()

    # 或者获取简要统计数据
    summary = get_library_string_count_summary()
    print(f"总共有 {summary['total_libraries']} 个库")






















